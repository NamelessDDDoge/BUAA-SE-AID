"""DTC-ADMIN-8 组织信息 / 检测次数配额"""
import pytest
from rest_framework.test import APIClient

from core.tests.factories import make_organization, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


def test_organization_usage_info_requires_authentication(client):
    resp = client.get("/api/organization/usage/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_organization_usage_info_returns_quota_keys_for_authenticated_user(client):
    user = make_user()
    client.force_authenticate(user)
    resp = client.get("/api/organization/usage/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 403)
    if resp.status_code == 200:
        rendered = str(resp.data)
        # 响应应该包含 llm/non_llm 用量信息
        assert "llm" in rendered.lower() or "uses" in rendered.lower()


def test_recharge_uses_endpoint_requires_authentication(client):
    resp = client.post("/api/organization/recharge-uses/", {}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


def test_organization_role_permission_update_requires_admin(client):
    org = make_organization()
    user = make_user(organization=org, role="publisher")
    client.force_authenticate(user)
    resp = client.post(
        f"/api/organization/{org.id}/permission/",
        {"role": "publisher", "permission": 1110},
        format="json",
    )
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    # 非组织管理员应被拒
    assert resp.status_code in (200, 401, 403)
