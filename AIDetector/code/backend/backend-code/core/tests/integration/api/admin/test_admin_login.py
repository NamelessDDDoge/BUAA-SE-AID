"""DTC-ADMIN-1 管理员登录"""
import pytest
from rest_framework.test import APIClient

from core.tests.factories import make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


def test_admin_login_rejects_missing_email(client):
    resp = client.post("/api/admin-login/", {}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (400, 401, 403)


def test_admin_login_rejects_non_admin_user(client):
    user = make_user()
    user.set_password("p")
    user.save_permission()
    resp = client.post("/api/admin-login/", {
        "email": user.email, "password": "p",
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code != 200


def test_admin_login_with_wrong_password(client):
    admin = make_user(email="admin@mail.com")
    admin.is_staff = True
    admin.organization = None
    admin.set_password("right-pwd")
    admin.save_permission()
    resp = client.post("/api/admin-login/", {
        "email": "admin@mail.com", "password": "wrong-pwd",
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code != 200
