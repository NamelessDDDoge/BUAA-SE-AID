import os


def get_active_model_config(model_type):
    try:
        from core.models import LLMModel

        model = (
            LLMModel.objects.filter(model_type=model_type, is_active=True)
            .order_by("-updated_at", "-created_at", "-id")
            .first()
        )
    except Exception:
        model = None

    if model:
        return {
            "endpoint": (model.endpoint or "").strip(),
            "model": (model.model_name or "").strip(),
            "key": (model.api_key or "").strip(),
            "provider": (model.provider or "").strip(),
        }
    return {}


def get_fastdetect_runtime_config(*, api_key=None, detector=None, endpoint=None):
    db_config = get_active_model_config("fastdetect")
    return {
        "endpoint": (
            (endpoint or "").strip()
            or db_config.get("endpoint", "")
            or os.environ.get("FASTDETECT_API_ENDPOINT", "").strip()
            or os.environ.get("DEFAULT_FASTDETECT_API_ENDPOINT", "").strip()
            or "https://api.fastdetect.net/api/detect"
        ),
        "model": (
            (detector or "").strip()
            or db_config.get("model", "")
            or os.environ.get("FASTDETECT_LLM_MODEL", "").strip()
            or os.environ.get("DEFAULT_FASTDETECT_MODEL", "").strip()
            or "fast-detect(llama3-8b/llama3-8b-instruct)"
        ),
        "key": (
            (api_key or "").strip()
            or db_config.get("key", "")
            or os.environ.get("FASTDETECT_API_KEY", "").strip()
            or os.environ.get("DEFAULT_FASTDETECT_API_KEY", "").strip()
            or ""
        ),
    }
