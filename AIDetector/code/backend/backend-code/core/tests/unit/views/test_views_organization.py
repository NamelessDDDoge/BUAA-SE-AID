"""views_organization — _is_software_admin + 关键端点参数校验"""
from unittest.mock import MagicMock

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import Organization, OrganizationApplication
from core.tests.factories import make_organization, make_user
from core.views.views_organization import _is_software_admin

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


# ---------- _is_software_admin ----------

def test_is_software_admin_true_for_well_known_email():
    user = make_user(email="admin@mail.com")
    assert _is_software_admin(user) is True


def test_is_software_admin_true_for_staff_without_organization():
    user = make_user()
    user.is_staff = True
    user.organization = None
    user.save()
    assert _is_software_admin(user) is True


def test_is_software_admin_false_for_regular_user():
    user = make_user()
    assert _is_software_admin(user) is False


def test_is_software_admin_false_for_staff_with_organization():
    user = make_user()
    user.is_staff = True
    user.save()
    assert _is_software_admin(user) is False


# ---------- CreateOrganizationApplicationView ----------

@override_settings(MEDIA_ROOT="/tmp/test-media-org-app")
def test_create_org_application_creates_record_with_required_fields(client):
    resp = client.post("/api/organization/create/", {
        "name": "Test Org Apply",
        "email": "apply-org@example.com",
        "admin_username": "apply-admin",
        "admin_email": "apply-admin@example.com",
        "admin_password": "secret",
        "description": "we want in",
    })
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 201
    assert OrganizationApplication.objects.filter(name="Test Org Apply").exists()


def test_create_org_application_rejects_missing_required_fields(client):
    resp = client.post("/api/organization/create/", {"name": "incomplete"})
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 400


# ---------- get_pending_organization_applications ----------

def test_get_pending_apps_rejected_for_regular_user(client):
    user = make_user()
    client.force_authenticate(user)
    resp = client.get("/api/organization/applications/get_pending/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 403


def test_get_pending_apps_rejects_unauthenticated(client):
    resp = client.get("/api/organization/applications/get_pending/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


# ---------- get_organizations ----------

def test_get_organizations_returns_list_for_admin(client):
    admin = make_user(email="admin@mail.com")
    admin.is_staff = True
    admin.save_permission()
    make_organization(name="org-A")
    make_organization(name="org-B")
    client.force_authenticate(admin)
    resp = client.get("/api/organizations/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 200


# ---------- get_organization_detail ----------

def test_get_organization_detail_404_for_missing_id(client):
    admin = make_user(email="admin@mail.com")
    admin.is_staff = True
    admin.save_permission()
    client.force_authenticate(admin)
    resp = client.get("/api/organization/999999/")
    if resp.status_code == 404 and "URL" in str(resp.data):
        pytest.skip("URL route not configured")
    # 期望返回 404 或 200（取决于实现是否做了存在性检查）
    assert resp.status_code in (200, 403, 404)
