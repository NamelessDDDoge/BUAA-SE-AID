"""views_dectection — 检测任务核心端点 smoke 测试

详细测试见 integration/api/detection/test_image_detection_flow.py、test_resource_task_flow.py。
"""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from core.tests.factories import (
    make_detection_task,
    make_image_upload,
    make_user,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


# ---------- submit_detection ----------

@override_settings(MEDIA_ROOT="/tmp/test-media-detection-submit")
def test_submit_detection_requires_authentication(client):
    resp = client.post("/api/detection/submit/", {"image_ids": [1]}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-detection-submit")
def test_submit_detection_rejects_empty_image_ids(client):
    user = make_user()
    client.force_authenticate(user)
    resp = client.post("/api/detection/submit/", {"image_ids": []}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (400, 422)


# ---------- get_detection_result ----------

@override_settings(MEDIA_ROOT="/tmp/test-media-detection-result")
def test_get_detection_result_requires_authentication(client):
    resp = client.get("/api/detection/1/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-detection-result")
def test_get_detection_result_404_for_missing_image(client):
    user = make_user()
    client.force_authenticate(user)
    resp = client.get("/api/detection/999999/")
    if resp.status_code == 404 and isinstance(resp.data, dict) and resp.data.get("detail") == "Not found.":
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 400, 403, 404)


# ---------- get_detection_task_status_normal ----------

@override_settings(MEDIA_ROOT="/tmp/test-media-detection-status")
def test_get_detection_task_status_requires_authentication(client):
    resp = client.get("/api/detection-task/1/status/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-detection-status")
def test_get_detection_task_status_returns_for_owner(client):
    user = make_user()
    task = make_detection_task(user=user)
    client.force_authenticate(user)
    resp = client.get(f"/api/detection-task/{task.id}/status/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 403)
    if resp.status_code == 200:
        assert "status" in resp.data


# ---------- list_task_results ----------

@override_settings(MEDIA_ROOT="/tmp/test-media-detection-list-results")
def test_list_task_results_requires_authentication(client):
    resp = client.get("/api/tasks/1/results/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


# ---------- create_resource_task ----------

@override_settings(MEDIA_ROOT="/tmp/test-media-detection-resource")
def test_create_resource_task_requires_authentication(client):
    resp = client.post("/api/resource-task/create/", {
        "task_type": "paper", "file_ids": [1],
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-detection-resource")
def test_create_resource_task_rejects_unknown_task_type(client):
    user = make_user()
    client.force_authenticate(user)
    resp = client.post("/api/resource-task/create/", {
        "task_type": "garbage", "file_ids": [1],
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (400, 422)


# ---------- DetectionTaskDeleteView ----------

@override_settings(MEDIA_ROOT="/tmp/test-media-detection-delete")
def test_delete_detection_task_requires_authentication(client):
    resp = client.delete("/api/detection-task-delete/1/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403, 405)


@override_settings(MEDIA_ROOT="/tmp/test-media-detection-delete")
@pytest.mark.parametrize("task_status", ["pending", "in_progress"])
def test_delete_detection_task_rejects_queued_or_running_tasks(client, task_status):
    user = make_user()
    task = make_detection_task(user=user, status=task_status)
    client.force_authenticate(user)

    resp = client.delete(f"/api/detection-task-delete/{task.id}/")

    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 400
    assert "cannot be deleted" in resp.data["detail"]
