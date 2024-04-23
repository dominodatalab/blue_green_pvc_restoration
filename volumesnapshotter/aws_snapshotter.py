

import logging
from kubernetes import client, config
from kubernetes.client import ApiClient, CustomObjectsApi, ApiException
import os
import json
import sys


DEFAULT_COMPUTE_NAMESPACE = "domino-compute"
k8s_api_client = None
custom_objects_api = None
vs_group = "snapshot.storage.k8s.io"
vs_api_version = "v1"
vs_kind = 'VolumeSnapshot'
vsc_kind = 'VolumeSnapshotContent'



compute_namespace: str = os.environ.get(
    "COMPUTE_NAMESPACE", DEFAULT_COMPUTE_NAMESPACE
)



lvl: str = logging.getLevelName(os.environ.get("LOG_LEVEL", "WARNING"))
logging.basicConfig(
    level=lvl,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("aws-volume-snapshotter")
logger.setLevel(logging.INFO)

try:
    config.load_incluster_config()
except config.ConfigException:
    try:
        config.load_kube_config()
    except config.ConfigException:
        raise Exception("Could not configure kubernetes python client")


k8s_api_client: ApiClient = client.ApiClient()
core_v1_api = client.CoreV1Api(k8s_api_client)
custom_objects_api: CustomObjectsApi = client.CustomObjectsApi(k8s_api_client)

def list_volume_snapshots():
    snapshots_by_vsc_name = {}
    out: object = custom_objects_api.list_cluster_custom_object(
        vs_group, vs_api_version, vsc_kind.lower() + 's'
    )

    print("\nVolume Snapshot Contents:\n")
    for obj in out['items']:
        # Iterate over each custom object and print specific fields
        name = obj.get('metadata', {}).get('name')
        snapshot = obj.get('status', {}).get('snapshotHandle')
        snapshots_by_vsc_name[name] = snapshot

    out: object = custom_objects_api.list_namespaced_custom_object(
                vs_group, vs_api_version, compute_namespace, vs_kind.lower()+'s'
            )
    print("\nVolume Snapshots:\n")
    vs_list = []
    for obj in out['items']:
        # Iterate over each custom object and print specific fields
        vs_name = obj.get('metadata', {}).get('name')
        vsc_name = obj.get('status', {}).get('boundVolumeSnapshotContentName')
        ready_to_use = obj.get('status', {}).get('readyToUse')
        restore_size = obj.get('status', {}).get('restoreSize')
        aws_snapshot_name = None
        if vsc_name in snapshots_by_vsc_name:
            aws_snapshot_name = snapshots_by_vsc_name[vsc_name]
        vs_list.append({'vs_name':vs_name,
                        'vsc_name':vsc_name,
                        'aws_snapshot_name':aws_snapshot_name,
                        'ready_to_use':ready_to_use,
                        'restore_size': restore_size,
                        })

    return vs_list



def create_volume_snapshots():
    vs_list = []
    # List PVCs
    pvc_list = core_v1_api.list_namespaced_persistent_volume_claim(compute_namespace)

    # Print the list of PVCs
    compute_pvc_list = []
    for pvc in pvc_list.items:
        if (pvc.metadata.name.startswith('workspace-')):
            compute_pvc_list.append(pvc.metadata.name)

    print("----PersistentVolumeClaims----\n")
    for pvc_name in compute_pvc_list:
        logger.info(pvc_name)


    logger.info("---Create Volume Snapshot---")
    for pvc_name in compute_pvc_list:
        custom_object = {
            "apiVersion": f"{vs_group}/{vs_api_version}",
            "kind": vs_kind,
            "metadata": {
                "name": pvc_name,
                "namespace": compute_namespace
            },
            "spec": {"source":
                        {"persistentVolumeClaimName":pvc_name},
                         "volumeSnapshotClassName":"csi-aws-vsc"
                    }
        }
        vs = custom_objects_api.create_namespaced_custom_object(
                group=vs_group,
                version="v1",
                namespace=compute_namespace,
                plural=vs_kind.lower() + "s",
                body=custom_object)
        logger.info(pvc_name)
        vs_list.append(vs)
    return vs_list

def import_volume_snapshots(vs_name,snap_shot_name):
    vs_custom_object = {
        "apiVersion": f"{vs_group}/{vs_api_version}",
        "kind": vs_kind,
        "metadata": {
            "name": vs_name,
            "namespace": compute_namespace
        },
        "spec": {"source":
                     {"volumeSnapshotContentName": vs_name},
                 "volumeSnapshotClassName": "csi-aws-vsc"
                 }
    }
    vs = custom_objects_api.create_namespaced_custom_object(
        group=vs_group,
        version="v1",
        namespace=compute_namespace,
        plural=vs_kind.lower() + "s",
        body=vs_custom_object)
    vsc_custom_object = {
        "apiVersion": f"{vs_group}/{vs_api_version}",
        "kind": vsc_kind,
        "metadata": {
            "name": vs_name
        },
        "spec": {"volumeSnapshotRef":
                     {
                         "kind": vs_kind,
                         "name": vs_name,
                         "namespace" : compute_namespace
                     },
                    "source": {"snapshotHandle":snap_shot_name},
                    "driver" : "ebs.csi.aws.com",
                    "deletionPolicy" : "Delete",
                    "volumeSnapshotClassName": "csi-aws-vsc"
                 }
    }
    print(vsc_custom_object)


    vsc = custom_objects_api.create_cluster_custom_object(
        group=vs_group,
        version="v1",
        plural=vsc_kind.lower() + "s",
        body=vsc_custom_object)
    

    return vs, vsc

def delete_volume_snapshots():
    # Delete the custom object
    vs_list = list_volume_snapshots()

    for vs in vs_list:
        vs_name = vs['vs_name']
        vsc_name = vs['vsc_name']
        #snap_name = vs['aws_snapshot_name']

        obj = custom_objects_api.delete_namespaced_custom_object(
            group=vs_group,
            version=vs_api_version,
            namespace=compute_namespace,
            plural=vs_kind.lower() + "s",  # Pluralize the kind to get the object's plural name
            name=vs_name
        )
        vs_deleted = obj.get('metadata', {}).get('name')
        '''
        obj = custom_objects_api.delete_cluster_custom_object(
            group=vs_group,
            version=vs_api_version,
            plural=vsc_kind.lower() + "s",  # Pluralize the kind to get the object's plural name
            name=vsc_name
        )
        
        vsc_deleted = obj.get('metadata', {}).get('name')
        '''
        print(f'Deleted VolumeSnapshot {vs_deleted} and associated content {vsc_name}')

def create_pvc_from_volume_snapshots(vs_name,storage_class,restore_size):
    try:
        # Load kubeconfig file and create a Kubernetes client instance
        config.load_kube_config()
        v1 = client.CoreV1Api()
        # Define PVC metadata
        metadata = client.V1ObjectMeta(name=vs_name)
        # Define PVC spec
        spec = client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            storage_class_name=storage_class,
            resources=client.V1ResourceRequirements(
                requests={"storage": restore_size}
            ),
            data_source=client.V1TypedLocalObjectReference(name=vs_name, kind=vs_kind, api_group=vs_group)
        )

        # Define PVC object
        pvc = client.V1PersistentVolumeClaim(
            api_version="v1",
            kind="PersistentVolumeClaim",
            metadata=metadata,
            spec=spec
        )
        api_response = None
        # Check if PVC already exists
        try:
            v1.read_namespaced_persistent_volume_claim(name=vs_name, namespace=compute_namespace)
            api_response = v1.patch_namespaced_persistent_volume_claim(name=vs_name,
                                                                       namespace=compute_namespace,
                                                                       body=pvc)
            print(f"PVC '{vs_name}' patched successfully.")
        except ApiException as e:
            if e.status == 404:
                api_response = core_v1_api.create_namespaced_persistent_volume_claim(
                    namespace=compute_namespace,
                    body=pvc
                )
                print(f"PVC '{vs_name}' created successfully.")
            else:
                print("Error:", e)
    except ApiException as e:
        print("Error:", e)

    return api_response

# Example usage:
if __name__ == "__main__":
    vs_list = list_volume_snapshots()
    print(vs_list)
    # Specify the filename for the JSON file
    filename = '/tmp/data.json'

    # Write data to JSON file
    with open(filename, mode='w') as file:
        json.dump(vs_list, file, indent=4)
