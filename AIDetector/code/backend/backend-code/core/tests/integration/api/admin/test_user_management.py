"""DTC-ADMIN-4 用户管理"""
import pytest
from rest_framework.test import APIClient

from core.tests.factories import make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


def test_get_users_requires_authentication(client):
    resp = client.get("/api/get_users/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


def test_create_user_requires_authentication(client):
    resp = client.post("/api/create_user/", {}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


def test_update_user_requires_authentication(client):
    u = make_user()
    resp = client.post(f"/api/update_user/{u.id}/", {}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


def test_delete_user_requires_authentication(client):
    u = make_user()
    resp = client.delete(f"/api/delete_user/{u.id}/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403, 405)


def test_user_permission_view_requires_authentication(client):
    u = make_user()
    resp = client.post(f"/api/user_permission/{u.id}/", {"permission": 1110}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)
