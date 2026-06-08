from .llm import detect_text_segment


FASTDETECT_PREFLIGHT_TEXT = "This is a short FastDetect billing and availability preflight check."
SERVICE_UNAVAILABLE_FUSE_THRESHOLD = 2


class DetectionBillingUnavailableError(RuntimeError):
    """Raised when AIGC detection billing/quota is unavailable."""


def preflight_text_detection(*, api_key=None):
    """Fail fast before expensive document preprocessing when FastDetect billing is unavailable."""
    _detect_segment_probability(FASTDETECT_PREFLIGHT_TEXT, api_key=api_key)
    return True


def analyze_text_segments(segments, *, api_key=None, suspicious_threshold=0.5):
    results = []
    service_error_count = 0
    fuse_error = None
    for index, segment in enumerate(segments):
        if fuse_error:
            probability = 0.0
            details = {"error": fuse_error, "skipped_due_to_service_fuse": True}
        else:
            probability, details = _detect_segment_probability(segment, api_key=api_key)
        detection_error = _is_detection_error(details)
        if detection_error:
            ai_verdict, is_ai_confirmed, confidence_level = ("service_unavailable", False, "unknown")
            label = "unavailable"
            service_error_count += 1
            if service_error_count >= SERVICE_UNAVAILABLE_FUSE_THRESHOLD and fuse_error is None:
                fuse_error = (
                    "AIGC 检测服务连续不可用，已停止继续逐段请求，"
                    "以避免长时间等待。"
                )
        else:
            service_error_count = 0
            ai_verdict, is_ai_confirmed, confidence_level = _classify_ai_verdict(probability)
            label = "suspicious" if probability >= suspicious_threshold else "clean"
        reason = _build_verdict_reason(segment, probability, details, ai_verdict)
        merged_details = {
            **(details if isinstance(details, dict) else {"raw_details": details}),
            "ai_verdict": ai_verdict,
            "is_ai_confirmed": is_ai_confirmed,
            "confidence_level": confidence_level,
            "forgery_reason": reason,
        }
        results.append(
            {
                "paragraph_index": index,
                "text": segment,
                "probability": probability,
                "label": label,
                "details": merged_details,
                "ai_verdict": ai_verdict,
                "is_ai_confirmed": is_ai_confirmed,
                "forgery_reason": reason,
            }
        )
    return results


def _detect_segment_probability(segment, *, api_key=None):
    try:
        response_data = detect_text_segment(segment, api_key=api_key)
        payload = response_data.get("data", {})
        probability = float(payload.get("prob", 0) or 0)
        details = payload.get("details", {})
    except Exception as exc:
        if _is_billing_unavailable_error(str(exc)):
            raise DetectionBillingUnavailableError(
                "AIGC 检测服务额度/计费不可用，请检查 FastDetect API Key 的余额、额度或计费状态。"
            ) from exc
        probability = 0.0
        details = {"error": str(exc)}
    return probability, details


def _classify_ai_verdict(probability):
    score = float(probability or 0.0)
    if score >= 0.85:
        return "confirmed_ai", True, "very_high"
    if score >= 0.65:
        return "high_risk", False, "high"
    if score >= 0.5:
        return "suspicious", False, "medium"
    return "likely_human", False, "low"


def _build_verdict_reason(text, probability, details, ai_verdict):
    score = float(probability or 0.0)
    if isinstance(details, dict) and details.get("error"):
        return _build_service_error_reason(str(details.get("error")))

    text_len = len((text or "").strip())
    style_hint = "段落长度较短" if text_len < 80 else "段落具有完整叙述结构"

    if ai_verdict == "confirmed_ai":
        return f"AIGC 概率为 {score:.2f}，达到基本确认阈值；{style_hint}。"
    if ai_verdict == "high_risk":
        return f"AIGC 概率为 {score:.2f}，处于高风险区间，建议人工重点复核。"
    if ai_verdict == "suspicious":
        return f"AIGC 概率为 {score:.2f}，存在可疑特征，建议结合上下文复核。"
    if ai_verdict == "service_unavailable":
        return "检测服务当前不可用，无法给出可信的 AIGC 判定。"
    return f"AIGC 概率为 {score:.2f}，当前更接近人工写作。"


def _is_detection_error(details):
    return isinstance(details, dict) and bool(details.get("error"))


def _build_service_error_reason(error_text):
    normalized = (error_text or "").lower()
    if _is_billing_unavailable_error(normalized):
        return "AIGC 检测服务返回 402（额度/计费不可用），本段无法完成概率检测。"
    if "401" in normalized or "unauthorized" in normalized:
        return "AIGC 检测服务鉴权失败（401），请检查 API Key。"
    if "429" in normalized or "too many requests" in normalized:
        return "AIGC 检测服务触发限流（429），请稍后重试。"
    if "timeout" in normalized:
        return "AIGC 检测服务请求超时，本段结果不可用。"
    return f"检测服务异常，本段结果不可用：{error_text}"


def _is_billing_unavailable_error(error_text):
    normalized = (error_text or "").lower()
    return "402" in normalized or "payment required" in normalized
