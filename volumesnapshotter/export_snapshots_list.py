import aws_snapshotter as snapshotter
import sys
import json

if __name__ == "__main__":
    vs_list = snapshotter.list_volume_snapshots()
    # Specify the filename for the JSON file
    filename = sys.argv[1]
    # Write data to JSON file
    with open(filename, mode='w') as file:
        json.dump(vs_list, file, indent=4)
        json.dump(vs_list, sys.stdout, indent=4)