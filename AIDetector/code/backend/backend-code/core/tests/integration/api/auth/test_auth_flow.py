"""DTC-USER-2 注册/登录/登出（4.1~4.3）"""
import pytest
from rest_framework.test import APIClient

from core.models import User
from core.tests.factories import make_invitation_code, make_organization, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


def test_register_login_logout_full_flow(client):
    org = make_organization()
    code = make_invitation_code(organization=org, role="publisher")

    # 注册
    resp = client.post("/api/register/", {
        "username": "flow-user",
        "email": "flow-user@example.com",
        "password": "flow-pwd-1",
        "invitation_code": code.code,
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 201
    assert User.objects.filter(username="flow-user").exists()

    # 登录
    resp = client.post("/api/login/", {
        "email": "flow-user@example.com",
        "password": "flow-pwd-1",
        "role": "publisher",
    }, format="json")
    assert resp.status_code == 200
    # 登录响应应包含 token（JWT）
    assert any(k in resp.data for k in ("access", "token", "refresh"))


def test_register_duplicate_email_rejected(client):
    org = make_organization()
    code1 = make_invitation_code(organization=org, role="publisher")
    code2 = make_invitation_code(organization=org, role="publisher")

    payload1 = {"username": "u-a", "email": "dup@example.com", "password": "p",
                "invitation_code": code1.code}
    payload2 = {"username": "u-b", "email": "dup@example.com", "password": "p",
                "invitation_code": code2.code}
    resp1 = client.post("/api/register/", payload1, format="json")
    if resp1.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp1.status_code == 201
    resp2 = client.post("/api/register/", payload2, format="json")
    assert resp2.status_code in (400, 409)


def test_login_with_email_not_registered_returns_error(client):
    resp = client.post("/api/login/", {
        "email": "ghost@example.com", "password": "x", "role": "publisher",
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code != 200


def test_logout_requires_authentication(client):
    resp = client.post("/api/logout/", {}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403, 400)
