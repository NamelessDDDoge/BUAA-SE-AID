"""capabilities/text_detection_service"""
from unittest.mock import patch

import pytest

from core.services.capabilities import text_detection_service as svc

pytestmark = pytest.mark.unit


# ---------- _classify_ai_verdict ----------

@pytest.mark.parametrize("prob, expected_verdict, expected_confirmed, expected_level", [
    (0.85, "confirmed_ai", True, "very_high"),
    (0.90, "confirmed_ai", True, "very_high"),
    (1.00, "confirmed_ai", True, "very_high"),
    (0.65, "high_risk", False, "high"),
    (0.84, "high_risk", False, "high"),
    (0.50, "suspicious", False, "medium"),
    (0.64, "suspicious", False, "medium"),
    (0.49, "likely_human", False, "low"),
    (0.00, "likely_human", False, "low"),
])
def test_classify_ai_verdict_boundaries(prob, expected_verdict, expected_confirmed, expected_level):
    v, confirmed, level = svc._classify_ai_verdict(prob)
    assert v == expected_verdict
    assert confirmed is expected_confirmed
    assert level == expected_level


def test_classify_ai_verdict_treats_none_as_zero():
    assert svc._classify_ai_verdict(None) == ("likely_human", False, "low")


# ---------- _is_detection_error ----------

def test_is_detection_error_true_when_error_key_present():
    assert svc._is_detection_error({"error": "boom"}) is True


def test_is_detection_error_false_when_dict_has_no_error_key():
    assert svc._is_detection_error({"prob": 0.5}) is False


def test_is_detection_error_false_for_non_dict():
    assert svc._is_detection_error("oops") is False
    assert svc._is_detection_error(None) is False


# ---------- _build_service_error_reason ----------

@pytest.mark.parametrize("err, expected_substring", [
    ("HTTP 402 payment required", "402"),
    ("Unauthorized 401", "401"),
    ("429 Too Many Requests", "429"),
    ("connection timeout", "超时"),
    ("some random error", "异常"),
])
def test_build_service_error_reason_maps_known_http_codes(err, expected_substring):
    msg = svc._build_service_error_reason(err)
    assert expected_substring in msg


# ---------- _build_verdict_reason ----------

def test_build_verdict_reason_emits_service_error_when_details_has_error():
    msg = svc._build_verdict_reason("text", 0.0, {"error": "402 payment required"}, "service_unavailable")
    assert "402" in msg


def test_build_verdict_reason_uses_short_or_long_style_hint():
    short = svc._build_verdict_reason("a" * 50, 0.9, {}, "confirmed_ai")
    long = svc._build_verdict_reason("a" * 200, 0.9, {}, "confirmed_ai")
    assert "段落长度较短" in short
    assert "段落具有完整叙述结构" in long


def test_build_verdict_reason_for_each_verdict_type():
    assert "确认" in svc._build_verdict_reason("text", 0.9, {}, "confirmed_ai")
    assert "高风险" in svc._build_verdict_reason("text", 0.7, {}, "high_risk")
    assert "可疑" in svc._build_verdict_reason("text", 0.55, {}, "suspicious")
    assert "不可用" in svc._build_verdict_reason("text", 0.0, {}, "service_unavailable")
    assert "人工写作" in svc._build_verdict_reason("text", 0.1, {}, "likely_human")


# ---------- analyze_text_segments (mocked) ----------

def _fake_detect(prob, **details):
    """构造 detect_text_segment 的返回结构。"""
    return {"data": {"prob": prob, "details": details}}


@patch("core.services.capabilities.text_detection_service.detect_text_segment")
def test_analyze_text_segments_returns_label_suspicious_above_threshold(mock_detect):
    mock_detect.return_value = _fake_detect(0.7)
    out = svc.analyze_text_segments(["some segment text"], suspicious_threshold=0.5)
    assert len(out) == 1
    assert out[0]["label"] == "suspicious"
    assert out[0]["probability"] == 0.7
    assert out[0]["paragraph_index"] == 0
    assert out[0]["ai_verdict"] == "high_risk"
    assert out[0]["is_ai_confirmed"] is False


@patch("core.services.capabilities.text_detection_service.detect_text_segment")
def test_analyze_text_segments_returns_clean_below_threshold(mock_detect):
    mock_detect.return_value = _fake_detect(0.1)
    out = svc.analyze_text_segments(["a segment"], suspicious_threshold=0.5)
    assert out[0]["label"] == "clean"
    assert out[0]["ai_verdict"] == "likely_human"


@patch("core.services.capabilities.text_detection_service.detect_text_segment")
def test_analyze_text_segments_handles_detection_exception(mock_detect):
    mock_detect.side_effect = RuntimeError("backend explode")
    out = svc.analyze_text_segments(["x"], suspicious_threshold=0.5)
    assert out[0]["label"] == "unavailable"
    assert out[0]["ai_verdict"] == "service_unavailable"
    assert out[0]["probability"] == 0.0
    assert "异常" in out[0]["forgery_reason"]


@patch("core.services.capabilities.text_detection_service.detect_text_segment")
def test_analyze_text_segments_handles_402_payment(mock_detect):
    mock_detect.side_effect = RuntimeError("server 402 payment required")
    out = svc.analyze_text_segments(["x"])
    assert out[0]["label"] == "unavailable"
    assert "402" in out[0]["forgery_reason"]


@patch("core.services.capabilities.text_detection_service.detect_text_segment")
def test_analyze_text_segments_indexes_paragraphs(mock_detect):
    mock_detect.return_value = _fake_detect(0.2)
    out = svc.analyze_text_segments(["one", "two", "three"])
    assert [r["paragraph_index"] for r in out] == [0, 1, 2]


@patch("core.services.capabilities.text_detection_service.detect_text_segment")
def test_analyze_text_segments_confirmed_ai_at_85(mock_detect):
    mock_detect.return_value = _fake_detect(0.85)
    out = svc.analyze_text_segments(["x"], suspicious_threshold=0.5)
    assert out[0]["ai_verdict"] == "confirmed_ai"
    assert out[0]["is_ai_confirmed"] is True
