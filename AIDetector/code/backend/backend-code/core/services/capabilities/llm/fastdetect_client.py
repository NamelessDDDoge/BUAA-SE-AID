import requests

from .runtime_config import get_fastdetect_runtime_config


def detect_text_segment(text, *, api_key=None, detector=None, endpoint=None, timeout=30):
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
