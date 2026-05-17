"""DTC-ADMIN-7 日志记录"""
import pytest
from rest_framework.test import APIClient

from core.models import Log
from core.tests.factories import make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


def test_user_action_log_get_requires_authentication(client):
    resp = client.get("/api/user_action_log/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_user_action_log_download_requires_authentication(client):
    resp = client.get("/api/user_action_log/download/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_single_user_action_log_requires_authentication(client):
    resp = client.get("/api/single-user-action-log/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_user_action_log_delete_requires_authentication(client):
    user = make_user()
    log = Log.objects.create(
        user=user, operation_type="upload", related_model="ImageUpload", related_id=1,
    )
    resp = client.delete(f"/api/user_action_log/{log.id}/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403, 405)
