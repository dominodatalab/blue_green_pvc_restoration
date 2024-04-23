# Blue Green Domino in EKS - Restoration of workspace state

This repo develops the services needed to snapshot pvc's for workspaces in the Blue Domino EKS Environment and 
restore them back into the Green Domino EKS Environment.

This solution is general in the sense that is works across EKS clusters in separate VPCs


## Installation

We will describe what you need to install on the K8s cluster in both the Blue and Green environments.  
In the Blue/Green Domino install the K8s and AWS components. The details can be read at this [link](https://aws.amazon.com/blogs/containers/using-amazon-ebs-snapshots-for-persistent-storage-with-your-amazon-eks-cluster-by-leveraging-add-ons/)
We provide the full instructions below.

A full working step by step tutorial on how to perform the steps manually  is available internally in our
[Wiki](https://dominodatalab.atlassian.net/wiki/spaces/CS/pages/2541191169/Restoring+workspace+from+a+snapshot+from+across+Domino+installations+PoC+for+Blue+Green+Upgrades)

### Blue Environment

#### Configure the Blue K8s Cluster. 

SSH into a basition host for the Blue K8s cluster

```shell
cd $INSTALL_FOLDER
git clone https://github.com/kubernetes-csi/external-snapshotter.git
git clone https://github.com/kubernetes-sigs/aws-ebs-csi-driver.git

cd $INSTALL_FOLDER/external-snapshotter/client/config/crd
kubectl apply -k .

cd $INSTALL_FOLDER/external-snapshotter/deploy/kubernetes/snapshot-controller
kubectl apply -k .

kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/aws-ebs-csi-driver/master/examples/kubernetes/snapshot/manifests/classes/snapshotclass.yaml
```

#### Configure the Blue EKS Cluster. 

a. Next copy the contents of the `./terraform` folder into a new folder. Ex. `./working/blue`
b. Change the file `variales.tf` as follows:
```shell

variable "eks-cluster-name" {
  type = string
  default = ""
}

variable "custom-kms-key-policy" {
  type = string
  default = "blue-upgrade-kms-key-policy"
}



variable "kms_keys" {
  description = "List of KMS key ARNs"
  type        = list(string)
  default = ["arn:aws:kms:us-west-2:<BLUE_EKS_ACCOUNT_NO>:key/<BLUE_KMS_KEY_ID>"]
}
```
c. Apply the terraform 

```shell
cd ./working/blue/
terraform init
terraform plan
terraform apply
```


### Green Environment

#### Configure the Green K8s Cluster. 

SSH into a basition host for the Blue K8s cluster

```shell
cd $INSTALL_FOLDER
git clone https://github.com/kubernetes-csi/external-snapshotter.git
git clone https://github.com/kubernetes-sigs/aws-ebs-csi-driver.git

cd $INSTALL_FOLDER/external-snapshotter/client/config/crd
kubectl apply -k .

cd $INSTALL_FOLDER/external-snapshotter/deploy/kubernetes/snapshot-controller
kubectl apply -k .

kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/aws-ebs-csi-driver/master/examples/kubernetes/snapshot/manifests/classes/snapshotclass.yaml
```

#### Configure the Green EKS Cluster. 

a. Next copy the contents of the `./terraform` folder into a new folder. Ex. `./working/green`
b. Change the file `variales.tf` as follows:
```shell

variable "eks-cluster-name" {
  type = string
  default = ""
}

variable "custom-kms-key-policy" {
  type = string
  default = "green-upgrade-kms-key-policy"
}



variable "kms_keys" {
  description = "List of KMS key ARNs"
  type        = list(string)
  default = ["arn:aws:kms:us-west-2:<BLUE_EKS_ACCOUNT_NO>:key/<BLUE_KMS_KEY_ID>",
             "arn:aws:kms:us-west-2:<GREEN_EKS_ACCOUNT_NO>:key/<GREEN_KMS_KEY_ID>"]
}
```
c. Apply the terraform 

```shell
cd ./working/green/
terraform init
terraform plan
terraform apply
```

## Steps 

Follow these steps:

1. Take the snapshots of pvcs for workspaces in the Blue Domino in the `domino-compute` namespace. These PVC's have prefix `workspace-`
2. Export a list of these snapshots. Below is an example JSON from the [list](./export/export.json)
   ```json
    {
        "vs_name": "workspace-661eaf0ea8ad693ecbabdcff",
        "vsc_name": "workspace-661eaf0ea8ad693ecbabdcff",
        "aws_snapshot_name": "snap-0e8d846b296163474",
        "ready_to_use": true,
        "restore_size": "10Gi"
    }
   ```
The attributes mean the following:
   
| vs_name                        | vsc_name                      | aws_snapshot_name    | ready_to_use | restore_size |
|--------------------------------|-------------------------------|----------------------|--------------|--------------|
| VolumeSnapshot Name | VolumeSnapshot Content Name | Snapshot Name in AWS | IS_IT_READY_TO_USE         | Size of the PVC         |

3. Import these snapshots into the Green Environment and verify they are ready to use
4. If the `VolumeSnapshot` is in "ReadyToUse" state create the pvcs in the green environment

## Test the process 

## Blue Environment

1. Connect to the blue environment from an edge node with `kubeconfig` installed

2. Install the python packages need to run this code
   
```shell
git clone https://github.com/cerebrotech/bluegreencloudvolumesnapshotter
cd ./bluegreencloudvolumesnapshotter
pip install -r ./requirements.txt
```


3. Create Snapshots

```shell
# Remove all existing VolumeSnapshots
./volumesnapshotter/delete_all_snapshots.py 
./volumesnapshotter/blue_env_create_snapshots.py 
./volumesnapshotter/blue_env_export_snapshots_list /tmp/export.json
```

The `/tmp/export.json` contains the details about the snapshots and the associated
pvc in the Blue environment for the stopped workspaces

## Green Environment

1. Connect to the green environment from an edge node with `kubeconfig` installed

2. Install the python packages need to run this code

```shell
git clone https://github.com/cerebrotech/bluegreencloudvolumesnapshotter
cd ./bluegreencloudvolumesnapshotter
pip install -r ./requirements.txt
```

3. Import Snapshots

```shell
# First Remove all existing VolumeSnapshots
python ./volumesnapshotter/delete_all_snapshots.py 
python ./volumesnapshotter/green_env_import_snapshots.py  /tmp/export.json
python ./volumesnapshotter/export_snapshots_list.py /tmp/export.json
##Verify all VolumeSnapshots are ReadyToUse
python ./volumesnapshotter/green_env_create_pvc_from_snapshots.py 
```

4. Create PVCs

Verify all VolumeSnapshots are ReadyToUse
```shell
./volumesnapshotter/export_snapshots_list.py 
```

Create PVC's from Snapshots

```shell
./volumesnapshotter/green_env_create_pvc_from_snapshots.py 
```

## Next Steps


1. Extend to AKS and GKE
