import os


def _split_keys(value):
    """Split a comma/newline/whitespace separated key string into a clean list."""
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        raw = value
    else:
        raw = str(value).replace("\n", ",").split(",")
    return [k.strip() for k in raw if k and str(k).strip()]


def _dedupe(items):
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


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


def get_active_model_keys(model_type, _exclude_health=("invalid", "exhausted")):
    """Return api_keys of all active models of a type, most-recent first.

    Allows configuring multiple keys (one per active LLMModel row, or
    comma-separated within a single row) for fallback when one stops responding.

    跳过健康状态为 invalid / exhausted 的 key（已被探测标记为不可用）。
    全部被排除则返回 []，调用方自行处理报错。
    """
    try:
        from core.models import LLMModel

        models = (
            LLMModel.objects.filter(model_type=model_type, is_active=True)
            .exclude(health_status__in=_exclude_health)
            .order_by("-updated_at", "-created_at", "-id")
        )
        keys = []
        for model in models:
            keys.extend(_split_keys(model.api_key))
        return _dedupe(keys)
    except Exception:
        return []


def get_fastdetect_keys(*, api_key=None):
    """Collect candidate FastDetect keys in priority order for fallback.

    Order: explicit arg -> all active DB models -> env vars. Each source may
    itself contain multiple comma/newline separated keys. Duplicates removed.
    """
    keys = []
    keys.extend(_split_keys(api_key))
    keys.extend(get_active_model_keys("fastdetect"))
    keys.extend(_split_keys(os.environ.get("FASTDETECT_API_KEYS", "")))
    keys.extend(_split_keys(os.environ.get("FASTDETECT_API_KEY", "")))
    keys.extend(_split_keys(os.environ.get("DEFAULT_FASTDETECT_API_KEYS", "")))
    keys.extend(_split_keys(os.environ.get("DEFAULT_FASTDETECT_API_KEY", "")))
    return _dedupe(keys)


def get_fastdetect_runtime_config(*, api_key=None, detector=None, endpoint=None):
    db_config = get_active_model_config("fastdetect")
    keys = get_fastdetect_keys(api_key=api_key)
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
        "keys": keys,
        "key": keys[0] if keys else "",
    }
