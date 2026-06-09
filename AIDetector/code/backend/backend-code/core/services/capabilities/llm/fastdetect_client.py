import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .health import AVAILABLE, EXHAUSTED, INVALID, update_model_health
from .runtime_config import get_fastdetect_runtime_config

logger = logging.getLogger(__name__)

# HTTP statuses that mean "this key is not usable right now" -> try the next key.
# 401/403 auth, 402 quota/billing, 404 key not found, 408 timeout, 429 rate limit, 5xx server down.
_FALLBACK_STATUS = {401, 402, 403, 404, 408, 429}


def _should_fallback_status(status_code):
    return status_code in _FALLBACK_STATUS or status_code >= 500


def _find_db_model_by_key(key):
    """Look up an active FastDetect LLMModel whose api_key field contains *key*.

    返回第一个匹配的 model 实例，找不到返回 None。懒加载避免 import 循环。
    """
    try:
        from core.models import LLMModel

        for model in LLMModel.objects.filter(model_type="fastdetect", is_active=True):
            raw = (model.api_key or "").strip()
            # 支持逗号分隔：逐段匹配
            if any(k.strip() == key for k in raw.replace("\n", ",").split(",")):
                return model
    except Exception:
        pass
    return None


# ── 单段检测（串行 fallback） ──────────────────────────────────────────────────


def _request_with_keys(text, keys, endpoint, model, timeout=30):
    """Try *keys* in order for one segment; return (response_json, succeeded_key).

    Raises last exception if all keys fail.
    """
    last_exc = None
    for key in keys:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        }
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json={"detector": model, "text": text},
                timeout=timeout,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            continue

        status = response.status_code
        if status >= 400 and _should_fallback_status(status):
            last_exc = requests.HTTPError(f"{status} {response.reason}", response=response)
            # 402 → 额度耗尽，404 → 密钥无效，落 DB
            if status == 402:
                _maybe_update_health(key, EXHAUSTED, "Key credit exhausted")
            elif status == 404:
                _maybe_update_health(key, INVALID, "API key not found")
            continue

        response.raise_for_status()
        _maybe_update_health(key, AVAILABLE)
        return response.json(), key

    if last_exc is not None:
        raise last_exc
    raise requests.RequestException("No FastDetect API key configured.")


DEFAULT_FASTDETECT_TIMEOUT = int(os.environ.get("FASTDETECT_REQUEST_TIMEOUT", "8") or 8)


def detect_text_segment(text, *, api_key=None, detector=None, endpoint=None, timeout=None):
    if timeout is None:
        timeout = DEFAULT_FASTDETECT_TIMEOUT
    config = get_fastdetect_runtime_config(api_key=api_key, detector=detector, endpoint=endpoint)
    keys = config.get("keys") or [config.get("key", "")]
    result, _ = _request_with_keys(text, keys, config["endpoint"], config["model"], timeout=timeout)
    return result


# ── 批量并行检测（多 key 并发） ──────────────────────────────────────────────


def batch_detect_text_segments(segments, *, api_key=None, detector=None, endpoint=None,
                                timeout=30, max_workers=None, progress_callback=None):
    """Parallel FastDetect across all available API keys.

    Distributes segments round-robin across keys.  Each segment gets a primary
    key assigned; if that key fails it falls back to the remaining keys in that
    thread.  Returns list of response dicts ***in the same order as input***.
    A failed segment returns ``{}`` (caller handles gracefully).

    If *progress_callback* is provided, it is called as each segment completes:
    ``progress_callback(completed_count, total_count)`` — useful for progress bars.
    """
    config = get_fastdetect_runtime_config(api_key=api_key, detector=detector, endpoint=endpoint)
    keys = config.get("keys") or [config.get("key", "")]
    if not keys or not keys[0]:
        raise requests.RequestException("No FastDetect API key configured.")

    ep = config["endpoint"]
    model = config["model"]
    workers = max_workers or min(len(keys), 8)
    n = len(segments)

    results = [None] * n
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {}
        for i, seg in enumerate(segments):
            # primary key first (round-robin), rest as fallback
            primary = keys[i % len(keys)]
            ordered = [primary] + [k for k in keys if k != primary]
            future = executor.submit(_request_with_keys, seg, ordered, ep, model, timeout)
            future_map[future] = i

        _done_count = 0
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                resp_json, _ = future.result()
                results[idx] = resp_json
            except Exception as exc:
                logger.warning("batch_detect: segment #%d failed (%s)", idx, exc)
                # 返回与 _is_detection_error 兼容的错误结构
                results[idx] = {"data": {"prob": 0, "details": {"error": str(exc)}}}
            _done_count += 1
            if progress_callback:
                progress_callback(_done_count, n)

    return results


# ── 健康写入 ──────────────────────────────────────────────────────────────────


def _maybe_update_health(key, status, detail=""):
    """如果 key 对应 DB 中的 LLMModel 行，更新其健康状态；否则静默跳过。"""
    model = _find_db_model_by_key(key)
    if model is not None:
        update_model_health(model, status, detail)
