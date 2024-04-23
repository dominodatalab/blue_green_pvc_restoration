import aws_snapshotter as snapshotter
import sys
import json

if __name__ == "__main__":
    # Specify the filename for the JSON file
    filename = sys.argv[1]
    #filename = '/tmp/data.json'
    # Write data to JSON file
    snapshotter.delete_volume_snapshots()
    with open(filename, mode='r') as file:
        vs_list = json.load(file)
        for v in vs_list:
            vs_name=v['vs_name']
            aws_snapshot_name = v['aws_snapshot_name']
            print(f'Creating Volume Snapshot {vs_name}')
            vs, vsc = snapshotter.import_volume_snapshots(vs_name,aws_snapshot_name)
