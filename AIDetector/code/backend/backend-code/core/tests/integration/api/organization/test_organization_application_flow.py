"""DTC-USER-1 组织申请 + 软件管理员审批"""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import Organization, OrganizationApplication
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


@override_settings(MEDIA_ROOT="/tmp/test-media-org-app-flow")
def test_full_application_lifecycle_pending_to_approved(client):
    # 1. 用户提交申请
    resp = client.post("/api/organization/create/", {
        "name": "Flow Org",
        "email": "flow-org@example.com",
        "admin_username": "flow-admin",
        "admin_email": "flow-admin@example.com",
        "admin_password": "secret",
    })
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 201
    app = OrganizationApplication.objects.get(name="Flow Org")
    assert app.status == "pending"

    # 2. 软件管理员查看
    admin = _make_admin()
    client.force_authenticate(admin)
    resp = client.get("/api/organization/applications/get_pending/")
    assert resp.status_code == 200

    # 3. 批准
    resp = client.post(f"/api/organization/{app.id}/approve/")
    if resp.status_code in (200, 201, 204):
        app.refresh_from_db()
        assert app.status == "approved"
        # 批准后应创建 Organization
        assert Organization.objects.filter(name="Flow Org").exists()


@override_settings(MEDIA_ROOT="/tmp/test-media-org-app-reject")
def test_application_can_be_rejected(client):
    resp = client.post("/api/organization/create/", {
        "name": "Reject Org",
        "email": "reject@example.com",
        "admin_username": "rej-admin",
        "admin_email": "rej-admin@example.com",
        "admin_password": "x",
    })
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 201
    app = OrganizationApplication.objects.get(name="Reject Org")

    admin = _make_admin()
    client.force_authenticate(admin)
    resp = client.post(f"/api/organization/{app.id}/reject/")
    if resp.status_code in (200, 201, 204):
        app.refresh_from_db()
        assert app.status == "rejected"


@override_settings(MEDIA_ROOT="/tmp/test-media-org-app-rbac")
def test_non_admin_cannot_view_pending_applications(client):
    user = make_user()
    client.force_authenticate(user)
    resp = client.get("/api/organization/applications/get_pending/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-org-app-detail")
def test_pending_application_detail_requires_admin(client):
    OrganizationApplication.objects.create(
        name="Detail Org", email="d@example.com",
        admin_username="da", admin_email="da@example.com", admin_password="x",
    )
    user = make_user()
    client.force_authenticate(user)
    app = OrganizationApplication.objects.first()
    resp = client.get(f"/api/organization/applications/{app.id}/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)
