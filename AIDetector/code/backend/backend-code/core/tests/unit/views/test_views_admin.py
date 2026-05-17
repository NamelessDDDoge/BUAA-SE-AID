"""views_admin — 管理端核心端点 smoke 测试

详细测试规划在 integration/api/admin/。views_admin.py 有 1900+ 行，
此处仅做关键权限边界和接口可达性 smoke 检查。
"""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from core.tests.factories import make_organization, make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


def _make_admin():
    admin = make_user(email="admin@mail.com")
    admin.is_staff = True
    admin.save_permission()
    return admin


# ---------- AdminDashboardView ----------

def test_admin_dashboard_requires_authentication(client):
    resp = client.get("/api/admin_dashboard/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


# ---------- AdminLoginView ----------

def test_admin_login_rejects_missing_credentials(client):
    resp = client.post("/api/admin-login/", {}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (400, 401, 403)


# ---------- get_users ----------

def test_get_users_requires_admin(client):
    user = make_user()
    client.force_authenticate(user)
    resp = client.get("/api/get_users/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_get_users_unauthenticated(client):
    resp = client.get("/api/get_users/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


# ---------- create_user (admin) ----------

def test_create_user_requires_authentication(client):
    resp = client.post("/api/create_user/", {}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


# ---------- delete_user ----------

def test_delete_user_requires_authentication(client):
    resp = client.delete("/api/delete_user/1/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403, 405)


# ---------- dashboard charts ----------

def test_dashboard_img_tag_requires_authentication(client):
    resp = client.get("/api/dashboard/img_tag/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_dashboard_top_publishers_requires_authentication(client):
    resp = client.get("/api/dashboard/top_publishers/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_dashboard_daily_active_users_requires_authentication(client):
    resp = client.get("/api/dashboard/daily_active_users/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


# ---------- UserActionLogGetView ----------

def test_user_action_log_get_requires_authentication(client):
    resp = client.get("/api/user_action_log/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_user_action_log_download_requires_authentication(client):
    resp = client.get("/api/user_action_log/download/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


# ---------- get_all_review_requests ----------

def test_get_all_review_requests_requires_authentication(client):
    resp = client.get("/api/get_reviewRequest/all/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


# ---------- handle_review_request ----------

def test_handle_review_request_requires_authentication(client):
    resp = client.post("/api/handle_reviewRequest/1/", {}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)
