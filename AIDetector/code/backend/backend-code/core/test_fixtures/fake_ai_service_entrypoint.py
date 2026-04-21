import base64
import json
import os
import pickle
import zipfile
from pathlib import Path

import numpy as np


shared_dir = Path(os.environ["AI_SERVICE_TEST_DIR"])
with zipfile.ZipFile(shared_dir / "img.zip") as zip_file:
    image_names = sorted(
        item.filename for item in zip_file.infolist() if item.filename.lower().endswith((".png", ".jpg", ".jpeg"))
    )
with open(shared_dir / "data.json", "r", encoding="utf-8") as handle:
    params = json.load(handle)

llm_results = []
ela_results = []
exif_results = []
splicing_results = []
blurring_results = []
bruteforce_results = []
contrast_results = []
inpainting_results = []
for index, image_name in enumerate(image_names):
    llm_results.append((image_name, (f"fake ai service saw {image_name} with block={params['cmd_block_size']}", None)))
    ela_results.append((image_name, np.full((12, 12), index + 1, dtype=np.uint8)))
    exif_results.append((image_name, None))
    prob = 0.95 if index == 1 else 0.10
    splicing_results.extend([np.full((12, 12), index, dtype=np.float32), prob])
    blurring_results.extend([np.zeros((12, 12), dtype=np.float32), 0.05])
    bruteforce_results.extend([np.zeros((12, 12), dtype=np.float32), 0.05])
    contrast_results.extend([np.zeros((12, 12), dtype=np.float32), 0.05])
    inpainting_results.extend([np.zeros((12, 12), dtype=np.float32), 0.05])

payload = [
    ("llm", llm_results),
    ("ela", ela_results),
    ("exif", exif_results),
    ("cmd", []),
    ("splicing", splicing_results),
    ("blurring", blurring_results),
    ("bruteforce", bruteforce_results),
    ("contrast", contrast_results),
    ("inpainting", inpainting_results),
]

print("start results", flush=True)
print(base64.b64encode(pickle.dumps(payload)).decode("utf-8"), flush=True)
