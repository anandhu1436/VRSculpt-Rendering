import thingi10k
import shutil
import os

# Initialize the dataset (download if not present)
# Use the 'raw' variant to get the original mesh files (e.g., STL, OBJ)
thingi10k.init(variant='raw')

# Set output directory for downloaded files
output_dir = "/Users/amaldevparakkat/Dropbox/ESurf/closed_models"
os.makedirs(output_dir, exist_ok=True)

# Iterate over all closed models in the dataset
for entry in thingi10k.dataset(closed=True):
    src_path = entry['file_path']  # Local path to the downloaded file in cache
    file_id = entry['file_id']
    file_ext = os.path.splitext(src_path)[1]
    dst_path = os.path.join(output_dir, f"{file_id}{file_ext}")
    shutil.copy(src_path, dst_path)
    print(f"Downloaded: {dst_path}")
