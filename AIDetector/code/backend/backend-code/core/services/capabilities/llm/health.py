"""FastDetect key 健康判定 (共享逻辑)。

基于对真实 /api/detect 的实测：
- 成功:        HTTP 200 + {"code":0,...,"msg":"Succeed"}
- 额度耗尽:     HTTP 402 + {"code":402,"msg":"Key credit exhausted (100.0000/100.0000)","data":null}
- 密钥无效:     HTTP 401/403 + 认证错误
- 暂时性:       429/408/5xx / 超时 / 连接错误

DB 写入:
- update_model_health(model, status, ...)   — 单行写入
- check_single_model(model, ...)            — 探测 + 写入
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import requests

from django.utils import timezone

logger = logging.getLogger(__name__)

# 健康状态枚举 (与 LLMModel.HEALTH_STATUS_CHOICES 对齐)
AVAILABLE = "available"
EXHAUSTED = "exhausted"
INVALID = "invalid"
ERROR = "error"

_CREDIT_RE = re.compile(r"\(\s*([\d.]+)\s*/\s*([\d.]+)\s*\)")


def _extract_msg(body):
    if not isinstance(body, dict):
        return ""
    msg = body.get("msg")
    if msg:
        return str(msg)
    err = body.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or "")
    if err:
        return str(err)
    return ""


def classify_fastdetect_response(status, body):
    """把一次 detect 响应归类为健康状态。

    参数:
        status: HTTP 状态码 (int)
        body:   已解析的响应体 (dict)，无法解析时传 None
    返回:
        (health_status, detail_msg)
    """
    code = body.get("code") if isinstance(body, dict) else None
    msg = _extract_msg(body)
    low = msg.lower()

    # 1. 成功
    if status == 200 and (code in (0, None)) and "exhausted" not in low:
        return AVAILABLE, ""

    # 2. 额度耗尽 (明确可判，不靠超时)
    if status == 402 or code == 402 or "credit exhausted" in low or "exhausted" in low:
        return EXHAUSTED, msg or "Key credit exhausted"

    # 3. 密钥无效 / 认证失败
    if status in (401, 403):
        return INVALID, msg or f"HTTP {status} authentication failed"

    # 4. 暂时性 (限流 / 超时 / 服务器错误 / 其余 4xx)
    return ERROR, msg or f"HTTP {status}"


def parse_credit(msg):
    """从 msg 抠出 (已用, 总额)，抠不到返回 None。"""
    if not msg:
        return None
    m = _CREDIT_RE.search(str(msg))
    if not m:
        return None
    try:
        return float(m.group(1)), float(m.group(2))
    except (TypeError, ValueError):
        return None


# ── DB 写入 ──────────────────────────────────────────────────────────────────


def update_model_health(model, status, detail="", credit=None):
    """将健康判定结果写入 LLMModel 行。不抛异常。

    参数:
        model: LLMModel 实例（已 save() 到 DB）。
        status: health.py 常量 (AVAILABLE/EXHAUSTED/INVALID/ERROR)。
        detail: 详情消息，如 HTTP 返回的 msg。
        credit: (used, total) 二元组或 None。
    """
    model.health_status = status
    model.health_detail = (detail or "")[:500]
    model.health_checked_at = timezone.now()
    if credit is not None:
        model.credit_used, model.credit_total = float(credit[0]), float(credit[1])
    try:
        model.save(update_fields=[
            "health_status", "health_detail", "health_checked_at",
            "credit_used", "credit_total",
        ])
    except Exception as exc:
        logger.warning("Failed to save health for model %d: %s", model.pk, exc)


def check_single_model(model, timeout=15):
    """对单个 LLMModel 发一次探测请求，将结果写入 DB。

    网络错误 / HTTP 错误全捕捉不会外抛。返回 (status, detail)。

    参数:
        model: LLMModel 实例（需要 endpoint 和 api_key 非空）。
        timeout: requests 超时秒数，默认 15。

    返回:
        (status_str, detail_str)
    """
    if not model.endpoint or not model.api_key:
        update_model_health(model, ERROR, "Missing endpoint or api_key")
        return ERROR, "Missing endpoint or api_key"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {model.api_key.strip()}",
    }
    payload = {"detector": "fast-detect(llama3-8b/llama3-8b-instruct)", "text": "probe"}

    try:
        resp = requests.post(model.endpoint.strip(), headers=headers, json=payload, timeout=timeout)
        status_code = resp.status_code
        try:
            body = resp.json()
        except Exception:
            body = None
    except (requests.ConnectionError, requests.Timeout) as exc:
        update_model_health(model, ERROR, str(type(exc).__name__))
        return ERROR, str(type(exc).__name__)
    except Exception as exc:
        update_model_health(model, ERROR, f"Unexpected: {exc}")
        return ERROR, f"Unexpected: {exc}"

    health_status, detail = classify_fastdetect_response(status_code, body)
    credit = parse_credit(detail)
    update_model_health(model, health_status, detail, credit=credit)
    return health_status, detail
