import aws_snapshotter as snapshotter
import sys
import json

if __name__ == "__main__":
    # Specify the filename for the JSON file
    filename = sys.argv[1]
    #filename = '/tmp/data.json'
    # Write data to JSON file

    with open(filename, mode='r') as file:
        vs_list = json.load(file)
        for v in vs_list:
            vs_name = v['vs_name']
            storage_class = 'dominodisk'
            restore_size = v['restore_size']

            print(f'Creating/Patching PVC {vs_name}')
            resp = snapshotter.create_pvc_from_volume_snapshots(vs_name,storage_class,restore_size)
            print(resp)
