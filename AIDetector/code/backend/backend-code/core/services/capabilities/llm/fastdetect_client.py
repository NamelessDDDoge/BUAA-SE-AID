import os

import requests

from .runtime_config import get_fastdetect_runtime_config


DEFAULT_FASTDETECT_TIMEOUT = int(os.environ.get("FASTDETECT_REQUEST_TIMEOUT", "8") or 8)


def detect_text_segment(text, *, api_key=None, detector=None, endpoint=None, timeout=None):
    if timeout is None:
        timeout = DEFAULT_FASTDETECT_TIMEOUT
    config = get_fastdetect_runtime_config(api_key=api_key, detector=detector, endpoint=endpoint)
    payload = {
        "detector": config["model"],
        "text": text,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['key']}",
    }
    response = requests.post(
        config["endpoint"],
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
