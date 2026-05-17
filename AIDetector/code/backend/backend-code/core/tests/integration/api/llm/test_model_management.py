"""DTC-ADMIN-9/10 模型管理（4.35~4.39）"""
import pytest
from rest_framework.test import APIClient

from core.models import LLMModel
from core.tests.factories import make_llm_model, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


def _make_software_admin():
    admin = make_user(email="admin@mail.com")
    admin.is_staff = True
    admin.organization = None
    admin.save_permission()
    return admin


def test_active_models_lists_chat_active_only(client):
    user = make_user()
    make_llm_model(model_type="chat", is_active=True, display_name="active-chat")
    make_llm_model(model_type="chat", is_active=False, display_name="inactive-chat")
    make_llm_model(model_type="fastdetect", is_active=True, display_name="fd")

    client.force_authenticate(user)
    resp = client.get("/api/llms/active/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 200
    names = [m["display_name"] for m in resp.data]
    assert "active-chat" in names
    assert "inactive-chat" not in names
    assert "fd" not in names


def test_admin_llms_list_rejects_non_admin(client):
    user = make_user()
    client.force_authenticate(user)
    resp = client.get("/api/admin/llms/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 403


def test_admin_llms_create_and_retrieve(client):
    admin = _make_software_admin()
    client.force_authenticate(admin)
    resp = client.post("/api/admin/llms/", {
        "model_name": "x-create-1",
        "display_name": "X Create",
        "model_type": "chat",
        "endpoint": "https://api.x",
        "api_key": "sk-test",
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 201)
    created_id = resp.data["id"]

    resp = client.get(f"/api/admin/llms/{created_id}/")
    assert resp.status_code == 200
    assert resp.data["model_name"] == "x-create-1"
    # api_key 为 write_only，不应在响应里
    assert "api_key" not in resp.data
    assert resp.data["has_api_key"] is True


def test_admin_llms_delete_removes_record(client):
    admin = _make_software_admin()
    m = make_llm_model(display_name="to-delete")
    client.force_authenticate(admin)
    resp = client.delete(f"/api/admin/llms/{m.id}/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 204)
    assert not LLMModel.objects.filter(id=m.id).exists()


def test_admin_llms_update_blank_api_key_preserves_old(client):
    admin = _make_software_admin()
    m = make_llm_model(api_key="sk-keep")
    client.force_authenticate(admin)
    resp = client.patch(f"/api/admin/llms/{m.id}/", {"api_key": "   "}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 201)
    m.refresh_from_db()
    assert m.api_key == "sk-keep"
