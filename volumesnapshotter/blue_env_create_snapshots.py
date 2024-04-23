import aws_snapshotter as snapshotter
import sys
import json

if __name__ == "__main__":
    vs_list = snapshotter.create_volume_snapshots()
    for vs in vs_list:
        print(vs)
        print('---')