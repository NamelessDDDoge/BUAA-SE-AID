import requests


DEFAULT_FASTDETECT_API_ENDPOINT = "https://api.fastdetect.net/api/detect"
DEFAULT_FASTDETECT_MODEL = "fast-detect(llama3-8b/llama3-8b-instruct)"
DEFAULT_FASTDETECT_API_KEY = "sk-szcr9duUjGSmp6UaDQlsJku1zBG3Rr1NSjFoGLsvFb5VWVos"


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
