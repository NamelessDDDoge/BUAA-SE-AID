import os

import requests


DEFAULT_FASTDETECT_API_ENDPOINT = (
    os.environ.get("FASTDETECT_API_ENDPOINT", "").strip()
    or os.environ.get("DEFAULT_FASTDETECT_API_ENDPOINT", "").strip()
    or "https://api.fastdetect.net/api/detect"
)
DEFAULT_FASTDETECT_MODEL = (
    os.environ.get("FASTDETECT_LLM_MODEL", "").strip()
    or os.environ.get("DEFAULT_FASTDETECT_MODEL", "").strip()
    or "fast-detect(llama3-8b/llama3-8b-instruct)"
)
DEFAULT_FASTDETECT_API_KEY = (
    os.environ.get("FASTDETECT_API_KEY", "").strip()
    or os.environ.get("DEFAULT_FASTDETECT_API_KEY", "").strip()
    or ""
)


def detect_text_segment(text, *, api_key=None, detector=None, endpoint=None, timeout=30):
    payload = {
        "detector": detector or DEFAULT_FASTDETECT_MODEL,
        "text": text,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key or DEFAULT_FASTDETECT_API_KEY}",
    }
    response = requests.post(
        endpoint or DEFAULT_FASTDETECT_API_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
