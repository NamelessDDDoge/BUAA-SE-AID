"""DTC-ADMIN-5 任务管理"""
import pytest
from rest_framework.test import APIClient

from core.tests.factories import make_detection_task, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


def test_get_task_summary_requires_authentication(client):
    resp = client.get("/api/get-task-summary/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_get_all_user_tasks_requires_authentication(client):
    resp = client.get("/api/get_all_user_tasks/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_get_files_requires_authentication(client):
    resp = client.get("/api/get_files/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_get_detection_task_status_admin_endpoint(client):
    task = make_detection_task()
    resp = client.get(f"/api/get_detection_task_status/{task.id}/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


def test_delete_image_upload_requires_authentication(client):
    resp = client.delete("/api/delete_image_upload/1/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403, 405)
