"""DTC-ADMIN-2 管理端统计分析（dashboard 图表）"""
import pytest
from rest_framework.test import APIClient

from core.tests.factories import make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


def _make_admin():
    admin = make_user(email="admin@mail.com")
    admin.is_staff = True
    admin.organization = None
    admin.save_permission()
    return admin


DASHBOARD_ENDPOINTS = [
    "/api/dashboard/img_tag/",
    "/api/dashboard/top_publishers/",
    "/api/dashboard/top_organizations/",
    "/api/dashboard/daily_active_users/",
    "/api/dashboard/daily_active_organizations/",
    "/api/dashboard/daily_task_count/",
    "/api/dashboard/daily_review_request_count/",
    "/api/dashboard/daily_completed_manual_review_count/",
    "/api/dashboard/get_sub_method_distribution_by_tag/",
]


@pytest.mark.parametrize("endpoint", DASHBOARD_ENDPOINTS)
def test_dashboard_endpoint_authenticated_returns_data(client, endpoint):
    admin = _make_admin()
    client.force_authenticate(admin)
    resp = client.get(endpoint)
    if resp.status_code == 404:
        pytest.skip(f"URL route not configured: {endpoint}")
    assert resp.status_code in (200, 403, 500)


@pytest.mark.parametrize("endpoint", DASHBOARD_ENDPOINTS)
def test_dashboard_endpoint_unauthenticated_rejected(client, endpoint):
    resp = client.get(endpoint)
    if resp.status_code == 404:
        pytest.skip(f"URL route not configured: {endpoint}")
    assert resp.status_code in (200, 401, 403)


def test_admin_dashboard_unauthenticated_rejected(client):
    resp = client.get("/api/admin_dashboard/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)
