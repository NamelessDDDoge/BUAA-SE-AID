import base64
import json
import os
import pickle
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image


TEST_DIR = Path(
    os.environ.get(
        "AI_SERVICE_TEST_DIR",
        str(Path.home() / ".codex" / "memories" / ".ai_service_io"),
    )
)
ZIP_PATH = TEST_DIR / "img.zip"
JSON_PATH = TEST_DIR / "data.json"
TMP_DIR = Path.home() / ".codex" / "memories" / ".tmp_ai_service"
TORCH_HOME_DIR = Path.home() / ".codex" / "memories" / ".torch_cache"
TEST_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)
TORCH_HOME_DIR.mkdir(parents=True, exist_ok=True)
os.environ["TMP"] = str(TMP_DIR)
os.environ["TEMP"] = str(TMP_DIR)
os.environ["TMPDIR"] = str(TMP_DIR)
os.environ["TORCH_HOME"] = str(TORCH_HOME_DIR)
tempfile.tempdir = str(TMP_DIR)

from pipeline.pipeline_single_image import PipelineSingleImage


def load_images(zip_path):
    images = []
    with zipfile.ZipFile(zip_path) as zip_file:
        for zip_info in zip_file.infolist():
            if "/" in zip_info.filename:
                continue
            if not zip_info.filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                continue
            img = Image.open(BytesIO(zip_file.read(zip_info)))
            images.append(np.array(img))
    return images


def load_params(json_path):
    with open(json_path, "r", encoding="utf-8") as file:
        params = json.load(file)
    if not isinstance(params, dict):
        return {}
    return params


if __name__ == "__main__":
    pipeline = PipelineSingleImage()
    pipeline.clear_images()
    method_params = load_params(JSON_PATH)
    pipeline.set_method_parameters(method_params)
    pipeline.run_multi_images(load_images(ZIP_PATH))
    result_bytes = pickle.dumps(pipeline.get_results())
    print("start results", flush=True)
    print(base64.b64encode(result_bytes).decode("utf-8"), flush=True)
