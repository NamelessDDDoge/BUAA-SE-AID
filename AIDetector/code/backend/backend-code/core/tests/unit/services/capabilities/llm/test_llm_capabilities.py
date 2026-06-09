"""capabilities/llm — runtime_config 优先级 + fastdetect_client 错误处理"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from core.services.capabilities.llm import fastdetect_client as fc
from core.services.capabilities.llm import runtime_config as rc
from core.services.capabilities.llm import openai_client
from core.tests.factories import make_llm_model

pytestmark = pytest.mark.unit


# ---------- get_active_model_config ----------

@pytest.mark.django_db
def test_get_active_model_config_returns_empty_when_no_model():
    out = rc.get_active_model_config("chat")
    assert out == {}


@pytest.mark.django_db
def test_get_active_model_config_returns_matching_active_model():
    make_llm_model(model_type="chat", is_active=True, endpoint="https://api.x", api_key="k1")
    out = rc.get_active_model_config("chat")
    assert out["endpoint"] == "https://api.x"
    assert out["key"] == "k1"


@pytest.mark.django_db
def test_get_active_model_config_ignores_inactive_models():
    make_llm_model(model_type="chat", is_active=False, endpoint="https://hidden")
    out = rc.get_active_model_config("chat")
    assert out == {}


@pytest.mark.django_db
def test_get_active_model_config_only_returns_requested_type():
    make_llm_model(model_type="fastdetect", is_active=True, endpoint="https://fd")
    out = rc.get_active_model_config("chat")
    assert out == {}


@pytest.mark.django_db
def test_get_active_model_config_picks_most_recently_updated():
    make_llm_model(model_type="chat", display_name="older", endpoint="https://old")
    newer = make_llm_model(model_type="chat", display_name="newer", endpoint="https://new")
    # Save again to trigger updated_at refresh
    newer.save()
    out = rc.get_active_model_config("chat")
    assert out["endpoint"] == "https://new"


# ---------- get_fastdetect_runtime_config (优先级) ----------

@pytest.mark.django_db
def test_fastdetect_explicit_args_win_over_db_and_env(monkeypatch):
    make_llm_model(model_type="fastdetect", endpoint="https://db", api_key="db-key")
    monkeypatch.setenv("FASTDETECT_API_ENDPOINT", "https://env")
    monkeypatch.setenv("FASTDETECT_API_KEY", "env-key")
    out = rc.get_fastdetect_runtime_config(
        endpoint="https://explicit", api_key="explicit-key", detector="explicit-model",
    )
    assert out["endpoint"] == "https://explicit"
    assert out["key"] == "explicit-key"
    assert out["model"] == "explicit-model"


@pytest.mark.django_db
def test_fastdetect_db_value_wins_over_env(monkeypatch):
    make_llm_model(model_type="fastdetect", endpoint="https://db", api_key="db-key")
    monkeypatch.setenv("FASTDETECT_API_ENDPOINT", "https://env")
    monkeypatch.setenv("FASTDETECT_API_KEY", "env-key")
    out = rc.get_fastdetect_runtime_config()
    assert out["endpoint"] == "https://db"
    assert out["key"] == "db-key"


@pytest.mark.django_db
def test_fastdetect_env_used_when_no_db_and_no_explicit(monkeypatch):
    # 显式 mock 掉 DB 查询，避免测试间 LLMModel 行未回滚干扰
    monkeypatch.setattr(rc, "get_active_model_config", lambda *_args, **_kw: {})
    monkeypatch.setenv("FASTDETECT_API_ENDPOINT", "https://env")
    monkeypatch.setenv("FASTDETECT_API_KEY", "env-key")
    out = rc.get_fastdetect_runtime_config()
    assert out["endpoint"] == "https://env"
    assert out["key"] == "env-key"


@pytest.mark.django_db
def test_fastdetect_falls_back_to_hardcoded_endpoint(monkeypatch):
    monkeypatch.delenv("FASTDETECT_API_ENDPOINT", raising=False)
    monkeypatch.delenv("DEFAULT_FASTDETECT_API_ENDPOINT", raising=False)
    monkeypatch.delenv("FASTDETECT_API_KEY", raising=False)
    monkeypatch.delenv("DEFAULT_FASTDETECT_API_KEY", raising=False)
    out = rc.get_fastdetect_runtime_config()
    assert out["endpoint"] == "https://api.fastdetect.net/api/detect"
    assert out["key"] == ""


@pytest.mark.django_db
def test_fastdetect_strips_whitespace_from_explicit_args():
    out = rc.get_fastdetect_runtime_config(
        endpoint="  https://x  ", api_key="  k  ", detector="  d  ",
    )
    assert out["endpoint"] == "https://x"
    assert out["key"] == "k"
    assert out["model"] == "d"




# ---------- structured table data authenticity ----------

@patch("core.services.capabilities.llm.openai_client._request_structured_json")
def test_assess_table_authenticity_sends_headers_and_rows(mock_request):
    mock_request.return_value = {
        "risk_level": "medium",
        "reason": "Accuracy jump needs verification.",
        "evidence_summary": "Ours reaches 91.4 accuracy.",
        "suspicious_cells": ["Ours / Accuracy"],
    }

    out = openai_client.assess_table_authenticity(
        table={
            "table_index": 0,
            "source": "pdf_inferred",
            "page_number": 2,
            "row_count": 3,
            "column_count": 3,
            "headers": ["Method", "Accuracy", "F1"],
            "rows": [["Baseline", "81.2", "79.5"], ["Ours", "91.4", "90.1"]],
            "text": "Method | Accuracy | F1\nBaseline | 81.2 | 79.5\nOurs | 91.4 | 90.1",
        }
    )

    assert out["risk_level"] == "medium"
    assert out["suspicious_cells"] == ["Ours / Accuracy"]
    user_prompt = mock_request.call_args.kwargs["user_prompt"]
    assert 'headers_json: ["Method", "Accuracy", "F1"]' in user_prompt
    assert 'rows_json: [["Baseline", "81.2", "79.5"], ["Ours", "91.4", "90.1"]]' in user_prompt


@patch("core.services.capabilities.llm.openai_client._request_structured_json")
def test_summarize_data_authenticity_returns_llm_summary(mock_request):
    mock_request.return_value = {
        "risk_level": "low",
        "summary": "未发现明显数据异常，表格结构已纳入分析。",
        "key_points": ["分析了1个表格"],
    }

    out = openai_client.summarize_data_authenticity(
        findings=[],
        table_results=[{"table_index": 0, "risk_level": "none"}],
        analyzed_paragraph_count=2,
        table_count=1,
    )

    assert out["risk_level"] == "low"
    assert out["summary"] == "未发现明显数据异常，表格结构已纳入分析。"
    assert out["key_points"] == ["分析了1个表格"]


# ---------- 多 key 收集 ----------

@pytest.mark.django_db
def test_get_fastdetect_keys_splits_comma_separated_arg(monkeypatch):
    monkeypatch.setattr(rc, "get_active_model_keys", lambda *_a, **_k: [])
    monkeypatch.delenv("FASTDETECT_API_KEYS", raising=False)
    monkeypatch.delenv("FASTDETECT_API_KEY", raising=False)
    monkeypatch.delenv("DEFAULT_FASTDETECT_API_KEYS", raising=False)
    monkeypatch.delenv("DEFAULT_FASTDETECT_API_KEY", raising=False)
    keys = rc.get_fastdetect_keys(api_key="k1, k2 ,k3")
    assert keys == ["k1", "k2", "k3"]


@pytest.mark.django_db
def test_get_fastdetect_keys_merges_db_and_env_dedup(monkeypatch):
    monkeypatch.setattr(rc, "get_active_model_keys", lambda *_a, **_k: ["dbk", "shared"])
    monkeypatch.setenv("FASTDETECT_API_KEY", "shared,envk")
    monkeypatch.delenv("FASTDETECT_API_KEYS", raising=False)
    monkeypatch.delenv("DEFAULT_FASTDETECT_API_KEYS", raising=False)
    monkeypatch.delenv("DEFAULT_FASTDETECT_API_KEY", raising=False)
    keys = rc.get_fastdetect_keys()
    assert keys == ["dbk", "shared", "envk"]


@pytest.mark.django_db
def test_runtime_config_first_key_is_singular_key(monkeypatch):
    monkeypatch.setattr(rc, "get_active_model_config", lambda *_a, **_k: {})
    monkeypatch.setattr(rc, "get_active_model_keys", lambda *_a, **_k: [])
    out = rc.get_fastdetect_runtime_config(api_key="a,b")
    assert out["keys"] == ["a", "b"]
    assert out["key"] == "a"


# ---------- fastdetect_client fallback ----------

def _resp(status=200, body=None):
    r = MagicMock()
    r.status_code = status
    r.reason = "Err"
    r.json.return_value = body or {"data": {"prob": 0.9}}
    r.raise_for_status = MagicMock()
    return r


def test_client_falls_back_when_first_key_unreachable():
    cfg = {"endpoint": "https://x", "model": "m", "keys": ["k1", "k2"], "key": "k1"}
    ok = _resp()
    with patch.object(fc, "get_fastdetect_runtime_config", return_value=cfg), \
         patch.object(fc.requests, "post", side_effect=[requests.ConnectionError("down"), ok]) as post:
        out = fc.detect_text_segment("t")
    assert out == {"data": {"prob": 0.9}}
    assert post.call_count == 2
    assert "Bearer k2" in post.call_args_list[1].kwargs["headers"]["Authorization"]


def test_client_falls_back_on_429_status():
    cfg = {"endpoint": "https://x", "model": "m", "keys": ["k1", "k2"], "key": "k1"}
    with patch.object(fc, "get_fastdetect_runtime_config", return_value=cfg), \
         patch.object(fc.requests, "post", side_effect=[_resp(status=429), _resp()]) as post:
        out = fc.detect_text_segment("t")
    assert out == {"data": {"prob": 0.9}}
    assert post.call_count == 2


def test_client_raises_last_error_when_all_keys_fail():
    cfg = {"endpoint": "https://x", "model": "m", "keys": ["k1", "k2"], "key": "k1"}
    with patch.object(fc, "get_fastdetect_runtime_config", return_value=cfg), \
         patch.object(fc.requests, "post", side_effect=requests.Timeout("slow")):
        with pytest.raises(requests.Timeout):
            fc.detect_text_segment("t")


def test_client_uses_single_key_when_only_one_configured():
    cfg = {"endpoint": "https://x", "model": "m", "keys": ["only"], "key": "only"}
    with patch.object(fc, "get_fastdetect_runtime_config", return_value=cfg), \
         patch.object(fc.requests, "post", return_value=_resp()) as post:
        fc.detect_text_segment("t")
    assert post.call_count == 1
    assert "Bearer only" in post.call_args.kwargs["headers"]["Authorization"]


def test_client_with_empty_key_still_attempts_request():
    """When config has no keys, the or-fallback in detect_text_segment uses [key=""].
    The request is attempted; a network failure propagates as ConnectionError."""
    cfg = {"endpoint": "https://x", "model": "m", "keys": [], "key": ""}
    with patch.object(fc, "get_fastdetect_runtime_config", return_value=cfg), \
         patch.object(fc.requests, "post", side_effect=requests.ConnectionError("down")):
        with pytest.raises(requests.ConnectionError):
            fc.detect_text_segment("t")


def test_client_raises_on_last_key_fallback_status():
    """Last key returns 429 — no more keys, should call raise_for_status and bubble up."""
    cfg = {"endpoint": "https://x", "model": "m", "keys": ["only"], "key": "only"}
    bad = _resp(status=429)
    bad.raise_for_status.side_effect = requests.HTTPError("429")
    with patch.object(fc, "get_fastdetect_runtime_config", return_value=cfg), \
         patch.object(fc.requests, "post", return_value=bad):
        with pytest.raises(requests.HTTPError):
            fc.detect_text_segment("t")


def test_client_raises_immediately_on_non_fallback_4xx():
    """400 is not in _FALLBACK_STATUS — raise_for_status called on first response."""
    cfg = {"endpoint": "https://x", "model": "m", "keys": ["k1", "k2"], "key": "k1"}
    bad = _resp(status=400)
    bad.raise_for_status.side_effect = requests.HTTPError("400")
    with patch.object(fc, "get_fastdetect_runtime_config", return_value=cfg), \
         patch.object(fc.requests, "post", return_value=bad) as post:
        with pytest.raises(requests.HTTPError):
            fc.detect_text_segment("t")
    assert post.call_count == 1


def test_client_falls_back_on_all_fallback_statuses():
    """401, 402, 403, 404, 408, 5xx all trigger fallback to next key."""
    for status in (401, 402, 403, 404, 408, 500, 503):
        cfg = {"endpoint": "https://x", "model": "m", "keys": ["k1", "k2"], "key": "k1"}
        with patch.object(fc, "get_fastdetect_runtime_config", return_value=cfg), \
             patch.object(fc.requests, "post", side_effect=[_resp(status=status), _resp()]) as post:
            out = fc.detect_text_segment("t")
        assert out == {"data": {"prob": 0.9}}, f"status {status} should trigger fallback"
        assert post.call_count == 2, f"status {status} should have tried 2 keys"


# ---------- health.classify_fastdetect_response ----------

from core.services.capabilities.llm.health import (
    classify_fastdetect_response,
    parse_credit,
    AVAILABLE, EXHAUSTED, INVALID, ERROR,
)


def test_health_200_code0_is_available():
    status, _ = classify_fastdetect_response(200, {"code": 0, "msg": "Succeed"})
    assert status == AVAILABLE


def test_health_200_no_code_is_available():
    status, _ = classify_fastdetect_response(200, {"msg": "ok"})
    assert status == AVAILABLE


def test_health_200_exhausted_in_msg_is_exhausted():
    status, detail = classify_fastdetect_response(200, {"code": 0, "msg": "Key credit exhausted (100/100)"})
    assert status == EXHAUSTED
    assert "exhausted" in detail.lower()


def test_health_402_status_is_exhausted():
    status, detail = classify_fastdetect_response(402, {"code": 402, "msg": "Key credit exhausted (100.0000/100.0000)"})
    assert status == EXHAUSTED
    assert detail != ""


def test_health_code_402_in_body_is_exhausted():
    status, _ = classify_fastdetect_response(200, {"code": 402, "msg": "exhausted"})
    assert status == EXHAUSTED


def test_health_401_is_invalid():
    status, detail = classify_fastdetect_response(401, {"msg": "Unauthorized"})
    assert status == INVALID
    assert detail != ""


def test_health_403_is_invalid():
    status, _ = classify_fastdetect_response(403, {})
    assert status == INVALID


def test_health_429_is_error():
    status, _ = classify_fastdetect_response(429, {"msg": "rate limited"})
    assert status == ERROR


def test_health_408_is_error():
    status, _ = classify_fastdetect_response(408, {})
    assert status == ERROR


def test_health_500_is_error():
    status, _ = classify_fastdetect_response(500, None)
    assert status == ERROR


def test_health_none_body_handled():
    status, _ = classify_fastdetect_response(200, None)
    assert status == AVAILABLE


# ---------- health.parse_credit ----------

def test_parse_credit_extracts_used_and_total():
    result = parse_credit("Key credit exhausted (100.0000/100.0000)")
    assert result == (100.0, 100.0)


def test_parse_credit_partial_use():
    result = parse_credit("used (42.5/100.0)")
    assert result == (42.5, 100.0)


def test_parse_credit_no_pattern_returns_none():
    assert parse_credit("some random message") is None


def test_parse_credit_none_returns_none():
    assert parse_credit(None) is None


def test_parse_credit_empty_returns_none():
    assert parse_credit("") is None


# ---------- update_model_health ----------

from core.services.capabilities.llm.health import update_model_health, check_single_model


@pytest.mark.django_db
def test_update_model_health_writes_fields():
    model = make_llm_model(model_type="fastdetect")
    update_model_health(model, EXHAUSTED, "Key credit exhausted (42.0/100.0)", credit=(42.0, 100.0))
    model.refresh_from_db()
    assert model.health_status == "exhausted"
    assert model.health_detail == "Key credit exhausted (42.0/100.0)"
    assert model.credit_used == 42.0
    assert model.credit_total == 100.0
    assert model.health_checked_at is not None


@pytest.mark.django_db
def test_update_model_health_available_without_credit():
    model = make_llm_model(model_type="fastdetect")
    update_model_health(model, AVAILABLE)
    model.refresh_from_db()
    assert model.health_status == "available"
    assert model.health_detail == ""
    assert model.credit_used is None
    assert model.credit_total is None


# ---------- check_single_model ----------

def _mock_resp(status=200, body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = body or {"code": 0, "msg": "Succeed"}
    return r


@pytest.mark.django_db
def test_check_single_model_available(monkeypatch):
    model = make_llm_model(model_type="fastdetect", endpoint="https://fd.example.com", api_key="sk-valid")
    import core.services.capabilities.llm.health as health_mod
    monkeypatch.setattr(health_mod.requests, "post", lambda *a, **kw: _mock_resp(200))
    status, _ = check_single_model(model)
    assert status == AVAILABLE
    model.refresh_from_db()
    assert model.health_status == "available"


@pytest.mark.django_db
def test_check_single_model_exhausted(monkeypatch):
    model = make_llm_model(model_type="fastdetect", endpoint="https://fd.example.com", api_key="sk-exhausted")
    body = {"code": 402, "msg": "Key credit exhausted (100.0000/100.0000)"}
    import core.services.capabilities.llm.health as health_mod
    monkeypatch.setattr(health_mod.requests, "post", lambda *a, **kw: _mock_resp(402, body))
    status, _ = check_single_model(model)
    assert status == EXHAUSTED
    model.refresh_from_db()
    assert model.health_status == "exhausted"
    assert model.credit_used == 100.0
    assert model.credit_total == 100.0


@pytest.mark.django_db
def test_check_single_model_invalid(monkeypatch):
    model = make_llm_model(model_type="fastdetect", endpoint="https://fd.example.com", api_key="sk-bad")
    body = {"msg": "Unauthorized"}
    import core.services.capabilities.llm.health as health_mod
    monkeypatch.setattr(health_mod.requests, "post", lambda *a, **kw: _mock_resp(401, body))
    status, _ = check_single_model(model)
    assert status == INVALID
    model.refresh_from_db()
    assert model.health_status == "invalid"


@pytest.mark.django_db
def test_check_single_model_network_error(monkeypatch):
    model = make_llm_model(model_type="fastdetect", endpoint="https://fd.example.com", api_key="sk-down")
    import core.services.capabilities.llm.health as health_mod
    def _raise(*a, **kw):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(health_mod.requests, "post", _raise)
    status, _ = check_single_model(model)
    assert status == ERROR
    model.refresh_from_db()
    assert model.health_status == "error"


@pytest.mark.django_db
def test_check_single_model_no_endpoint():
    model = make_llm_model(model_type="fastdetect", endpoint="", api_key="sk-xxx")
    status, _ = check_single_model(model)
    assert status == ERROR
    model.refresh_from_db()
    assert model.health_status == "error"


# ---------- client + DB health integration ----------

@pytest.mark.django_db
def test_client_success_updates_db_health(monkeypatch):
    """detect_text_segment 成功后，对应的 LLMModel 行变为 available。"""
    key = "sk-db-healthy"
    make_llm_model(model_type="fastdetect", api_key=key, endpoint="https://db")
    cfg = {"endpoint": "https://db", "model": "m", "keys": [key], "key": key}
    monkeypatch.setattr(fc, "get_fastdetect_runtime_config", lambda **kw: cfg)
    monkeypatch.setattr(fc.requests, "post", lambda *a, **kw: _resp(200))

    fc.detect_text_segment("hello")

    model = rc.get_active_model_config("fastdetect")
    # 验证 DB 记录已更新
    from core.models import LLMModel
    db_model = LLMModel.objects.filter(api_key=key, model_type="fastdetect").first()
    assert db_model is not None
    assert db_model.health_status == "available"


@pytest.mark.django_db
def test_client_402_fallback_marks_exhausted(monkeypatch):
    """detect_text_segment fallback 因 402 时，对应模型标记为 exhausted。"""
    key1 = "sk-ex"
    key2 = "sk-ok"
    make_llm_model(model_type="fastdetect", api_key=key1, endpoint="https://db")
    make_llm_model(model_type="fastdetect", api_key=key2, endpoint="https://db")
    cfg = {"endpoint": "https://db", "model": "m", "keys": [key1, key2], "key": key1}
    monkeypatch.setattr(fc, "get_fastdetect_runtime_config", lambda **kw: cfg)
    with patch.object(fc.requests, "post", side_effect=[_resp(status=402), _resp()]):
        fc.detect_text_segment("hello")

    from core.models import LLMModel
    m1 = LLMModel.objects.get(api_key=key1)
    assert m1.health_status == "exhausted"
    m2 = LLMModel.objects.get(api_key=key2)
    assert m2.health_status == "available"
