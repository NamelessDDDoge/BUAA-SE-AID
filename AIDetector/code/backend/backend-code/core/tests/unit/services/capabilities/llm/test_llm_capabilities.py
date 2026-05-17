"""capabilities/llm — runtime_config 优先级 + fastdetect_client 错误处理"""
from unittest.mock import patch

import pytest

from core.services.capabilities.llm import runtime_config as rc
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
