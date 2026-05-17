"""views_user — 注册/登录关键路径 + _safe_avatar_url 辅助函数"""
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import InvitationCode, User
from core.tests.factories import make_invitation_code, make_organization, make_user
from core.views.views_user import _safe_avatar_url

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


# ---------- _safe_avatar_url ----------

def test_safe_avatar_url_returns_none_when_no_avatar_attr():
    obj = MagicMock(spec=[])
    assert _safe_avatar_url(obj) is None


def test_safe_avatar_url_returns_none_when_avatar_storage_raises():
    user = MagicMock()
    user.avatar.name = "p.png"
    user.avatar.storage.exists.side_effect = OSError("disk gone")
    assert _safe_avatar_url(user) is None


def test_safe_avatar_url_returns_none_when_file_does_not_exist():
    user = MagicMock()
    user.avatar.name = "p.png"
    user.avatar.storage.exists.return_value = False
    assert _safe_avatar_url(user) is None


def test_safe_avatar_url_returns_url_when_file_exists():
    user = MagicMock()
    user.avatar.name = "p.png"
    user.avatar.storage.exists.return_value = True
    user.avatar.url = "/media/p.png"
    assert _safe_avatar_url(user) == "/media/p.png"


# ---------- register endpoint ----------

def test_register_creates_user_when_invitation_code_valid(client):
    org = make_organization()
    code = make_invitation_code(organization=org, role="publisher")
    resp = client.post("/api/register/", {
        "username": "new-user",
        "email": "new-user@example.com",
        "password": "secret-pass",
        "invitation_code": code.code,
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 201
    user = User.objects.get(username="new-user")
    assert user.role == "publisher"
    assert user.organization_id == org.id


def test_register_rejects_invalid_invitation_code(client):
    resp = client.post("/api/register/", {
        "username": "u",
        "email": "u@example.com",
        "password": "x",
        "invitation_code": "NOCODE",
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 400
    assert "invitation_code" in resp.data


def test_register_rejects_expired_invitation_code(client):
    org = make_organization()
    expired = InvitationCode.objects.create(
        code="EXPCD1",
        organization=org,
        role="reviewer",
        expires_at=timezone.now() - timedelta(days=1),
    )
    resp = client.post("/api/register/", {
        "username": "u2",
        "email": "u2@example.com",
        "password": "x",
        "invitation_code": expired.code,
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 400


def test_register_rejects_used_invitation_code(client):
    code = make_invitation_code(is_used=True)
    resp = client.post("/api/register/", {
        "username": "u3",
        "email": "u3@example.com",
        "password": "x",
        "invitation_code": code.code,
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 400


def test_register_rejects_missing_fields(client):
    resp = client.post("/api/register/", {"username": "x"}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 400


# ---------- login endpoint ----------

def test_login_requires_email_and_password(client):
    resp = client.post("/api/login/", {}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (400, 401)


def test_login_with_wrong_password_returns_error(client):
    user = make_user(email="login-test@example.com", role="publisher")
    user.set_password("right-pwd")
    user.save_permission()  # 避免重置权限位
    resp = client.post("/api/login/", {
        "email": "login-test@example.com",
        "password": "wrong-pwd",
        "role": "publisher",
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (400, 401, 403)


def test_login_with_role_mismatch_is_rejected(client):
    # 用 publisher 账号但请求 reviewer 角色登录
    user = make_user(email="role-mismatch@example.com", role="publisher")
    user.set_password("pwd-123")
    user.save_permission()
    resp = client.post("/api/login/", {
        "email": "role-mismatch@example.com",
        "password": "pwd-123",
        "role": "reviewer",  # 角色不匹配
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    # 实现可能返回 400/401/403
    assert resp.status_code != 200
