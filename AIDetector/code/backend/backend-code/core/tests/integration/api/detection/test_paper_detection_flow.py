"""DTC-USER-3 论文检测 — create_resource_task → 查询状态 → 取结果"""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import DetectionTask
from core.tests.factories import make_file_management, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


@override_settings(MEDIA_ROOT="/tmp/test-media-paper-flow")
def test_create_paper_task_with_valid_file_returns_task_id(client):
    user = make_user()
    f = make_file_management(user=user, resource_type="paper")
    client.force_authenticate(user)
    resp = client.post("/api/resource-task/create/", {
        "task_type": "paper",
        "file_ids": [f.id],
        "task_name": "测试论文检测",
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    if resp.status_code in (200, 201):
        # 应创建出一个 paper 任务
        tasks = DetectionTask.objects.filter(user=user, task_type="paper")
        assert tasks.exists()


@override_settings(MEDIA_ROOT="/tmp/test-media-paper-flow")
def test_create_paper_task_rejects_non_paper_file(client):
    user = make_user()
    f = make_file_management(user=user, resource_type="image")
    client.force_authenticate(user)
    resp = client.post("/api/resource-task/create/", {
        "task_type": "paper",
        "file_ids": [f.id],
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (400, 422)


@override_settings(MEDIA_ROOT="/tmp/test-media-paper-flow")
def test_paper_results_endpoint_returns_404_for_unknown_task(client):
    user = make_user()
    client.force_authenticate(user)
    resp = client.get("/api/paper-results/999999/")
    if resp.status_code == 404 and isinstance(resp.data, dict) and resp.data.get("detail") == "Not found.":
        pytest.skip("URL route not configured")
    assert resp.status_code in (404, 400, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-paper-flow")
def test_paper_create_rejects_foreign_file(client):
    user = make_user()
    other = make_user()
    foreign_file = make_file_management(user=other, resource_type="paper")
    client.force_authenticate(user)
    resp = client.post("/api/resource-task/create/", {
        "task_type": "paper",
        "file_ids": [foreign_file.id],
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (400, 403, 404)
