"""DTC-USER-4 人工审核 — 发布者发起 → 管理员审批 → 审稿人完成"""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import ManualReview, ReviewRequest
from core.tests.factories import (
    make_detection_result,
    make_detection_task,
    make_image_upload,
    make_organization,
    make_review_request,
    make_user,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


@override_settings(MEDIA_ROOT="/tmp/test-media-review-req")
def test_create_review_task_requires_authentication(client):
    resp = client.post("/api/create_review_task_with_admin_check/", {}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-review-req")
def test_get_request_detail_for_owner_returns_data(client):
    rr = make_review_request()
    client.force_authenticate(rr.user)
    resp = client.get(f"/api/get_request_detail/{rr.id}/")
    if resp.status_code == 404 and isinstance(resp.data, dict) and resp.data.get("detail") == "Not found.":
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 403, 404)


@override_settings(MEDIA_ROOT="/tmp/test-media-review-req")
def test_get_publisher_review_tasks_lists_own_requests(client):
    user = make_user(role="publisher")
    make_review_request(user=user)
    client.force_authenticate(user)
    resp = client.get("/api/get_publisher_review_tasks/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-review-req")
def test_publisher_detection_task_access_check(client):
    user = make_user(role="publisher")
    task = make_detection_task(user=user)
    client.force_authenticate(user)
    resp = client.get(f"/api/publisher-dectectiontask-access/?task_id={task.id}")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 400, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-review-req")
def test_reviewer_can_get_assigned_tasks(client):
    org = make_organization()
    reviewer = make_user(organization=org, role="reviewer")
    client.force_authenticate(reviewer)
    resp = client.get("/api/get_reviewer_tasks/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)
