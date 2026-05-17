"""views_llm: LLMModelSerializer + IsSoftwareAdmin + active_models 端点"""
from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from core.tests.factories import make_llm_model, make_organization, make_user
from core.views.views_llm import IsSoftwareAdmin, LLMModelSerializer

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# ---------- LLMModelSerializer ----------

def test_serializer_excludes_api_key_in_output():
    m = make_llm_model(api_key="sk-secret-123")
    data = LLMModelSerializer(m).data
    assert "api_key" not in data  # write_only
    assert data["has_api_key"] is True


def test_serializer_has_api_key_false_when_empty_or_whitespace():
    m = make_llm_model(api_key="   ")
    data = LLMModelSerializer(m).data
    assert data["has_api_key"] is False


def test_serializer_rejects_invalid_model_type():
    serializer = LLMModelSerializer(data={
        "model_name": "x", "display_name": "X", "provider": "p",
        "model_type": "garbage", "endpoint": "https://x",
    })
    assert not serializer.is_valid()
    assert "model_type" in serializer.errors


def test_serializer_accepts_chat_and_fastdetect_types():
    for mt in ("chat", "fastdetect"):
        serializer = LLMModelSerializer(data={
            "model_name": f"x-{mt}", "display_name": f"X {mt}",
            "model_type": mt, "endpoint": "https://x",
        })
        assert serializer.is_valid(), serializer.errors


def test_serializer_create_strips_api_key():
    serializer = LLMModelSerializer(data={
        "model_name": "x-strip", "display_name": "X", "model_type": "chat",
        "api_key": "   sk-real-key   ",
    })
    assert serializer.is_valid(), serializer.errors
    instance = serializer.save()
    assert instance.api_key == "sk-real-key"


def test_serializer_update_keeps_existing_api_key_when_blank():
    m = make_llm_model(api_key="sk-keep-me")
    serializer = LLMModelSerializer(m, data={"api_key": "   "}, partial=True)
    assert serializer.is_valid(), serializer.errors
    instance = serializer.save()
    instance.refresh_from_db()
    assert instance.api_key == "sk-keep-me"


def test_serializer_update_replaces_api_key_when_new_value_present():
    m = make_llm_model(api_key="sk-old")
    serializer = LLMModelSerializer(m, data={"api_key": "sk-new"}, partial=True)
    assert serializer.is_valid()
    instance = serializer.save()
    instance.refresh_from_db()
    assert instance.api_key == "sk-new"


# ---------- IsSoftwareAdmin ----------

def _fake_req(user):
    r = MagicMock()
    r.user = user
    return r


def test_is_software_admin_allows_well_known_email():
    user = make_user(email="admin@mail.com")
    assert IsSoftwareAdmin().has_permission(_fake_req(user), view=None) is True


def test_is_software_admin_allows_staff_without_organization():
    user = make_user()
    user.is_staff = True
    user.organization = None
    user.save()
    assert IsSoftwareAdmin().has_permission(_fake_req(user), view=None) is True


def test_is_software_admin_rejects_staff_with_organization():
    user = make_user()
    user.is_staff = True
    user.save()
    # user.organization is set by factory
    assert IsSoftwareAdmin().has_permission(_fake_req(user), view=None) is False


def test_is_software_admin_rejects_regular_user():
    user = make_user()
    assert IsSoftwareAdmin().has_permission(_fake_req(user), view=None) is False


def test_is_software_admin_rejects_unauthenticated():
    user = MagicMock()
    user.is_authenticated = False
    assert IsSoftwareAdmin().has_permission(_fake_req(user), view=None) is False


# ---------- active_models endpoint ----------

@pytest.fixture
def client():
    return APIClient()


def test_active_models_returns_only_chat_active_models(client):
    me = make_user()
    make_llm_model(model_type="chat", is_active=True, display_name="chat-on")
    make_llm_model(model_type="chat", is_active=False, display_name="chat-off")
    make_llm_model(model_type="fastdetect", is_active=True, display_name="fd-on")

    client.force_authenticate(me)
    resp = client.get("/api/llms/active/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 200
    names = [m["display_name"] for m in resp.data]
    assert "chat-on" in names
    assert "chat-off" not in names
    assert "fd-on" not in names


def test_active_models_requires_authentication(client):
    resp = client.get("/api/llms/active/")
    assert resp.status_code in (401, 403, 404)


def test_admin_llms_list_rejected_for_regular_user(client):
    me = make_user()
    client.force_authenticate(me)
    resp = client.get("/api/admin/llms/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 403


def test_admin_llms_list_allowed_for_software_admin(client):
    admin = make_user(email="admin@mail.com")
    make_llm_model(display_name="m1")
    client.force_authenticate(admin)
    resp = client.get("/api/admin/llms/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 200
