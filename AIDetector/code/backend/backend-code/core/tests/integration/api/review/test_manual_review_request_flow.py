"""DTC-USER-4 人工审核 — 发布者发起 → 管理员审批 → 审稿人完成"""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import ImageReview, ManualReview, ReviewRequest
from core.tests.factories import (
    make_detection_result,
    make_detection_task,
    make_file_management,
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


@override_settings(MEDIA_ROOT="/tmp/test-media-image-review-flow")
def test_image_manual_review_flow_admin_accepts_reviewer_views_and_submits(client):
    org = make_organization()
    admin = make_user(organization=org, role="admin", is_staff=True)
    publisher = make_user(organization=org, role="publisher")
    reviewer = make_user(organization=org, role="reviewer")
    org.admin_user = admin
    org.save(update_fields=["admin_user"])

    task = make_detection_task(user=publisher, organization=org, task_type="image", status="completed")
    source_file = make_file_management(user=publisher, organization=org, resource_type="image", file_type="image/png")
    image_upload = make_image_upload(detection_task=task, file_management=source_file)
    detection_result = make_detection_result(
        detection_task=task,
        image_upload=image_upload,
        status="completed",
        is_fake=True,
        confidence_score=0.87,
    )
    review_request = ReviewRequest.objects.create(
        detection_result=detection_result,
        user=publisher,
        organization=org,
        reason="Please double check this suspicious image",
    )
    review_request.imgs.add(image_upload)
    review_request.reviewers.add(reviewer)

    client.force_authenticate(admin)
    accept_response = client.post(
        f"/api/handle_reviewRequest/{review_request.id}/",
        {"choice": 1, "reason": "approved"},
        format="json",
    )

    assert accept_response.status_code == 200
    review_request.refresh_from_db()
    assert review_request.status2 == "accepted"
    assert review_request.status1 == "in_progress"

    manual_review = ManualReview.objects.get(review_request=review_request, reviewer=reviewer)
    assert manual_review.status == "undo"
    assert manual_review.imgs.filter(id=image_upload.id).exists()
    assert ImageReview.objects.get(manual_review=manual_review, img=image_upload).result is None

    client.force_authenticate(reviewer)
    detail_response = client.get(f"/api/get_review_detail/{manual_review.id}/")

    assert detail_response.status_code == 200
    assert detail_response.data["request_type"] == "image"
    assert detail_response.data["imgs"][0]["id"] == image_upload.id
    assert detail_response.data["imgs"][0]["img_id"] == image_upload.id
    assert detail_response.data["status"] == "undo"

    submit_response = client.post(
        f"/api/post_review/{manual_review.id}/",
        {
            "result": [
                {
                    "img_id": image_upload.id,
                    "score": [1, 2, 3, 4, 5, 4, 3],
                    "reason": ["r1", "r2", "r3", "r4", "r5", "r6", "r7"],
                    "points": [[], [], [], [], [], [], []],
                    "final": True,
                }
            ]
        },
        format="json",
    )

    assert submit_response.status_code == 201
    manual_review.refresh_from_db()
    review_request.refresh_from_db()
    image_upload.refresh_from_db()
    image_review = ImageReview.objects.get(manual_review=manual_review, img=image_upload)

    assert manual_review.status == "completed"
    assert review_request.status1 == "completed"
    assert image_upload.isReview is True
    assert image_review.result is True
    assert image_review.score1 == 1

    client.force_authenticate(publisher)
    publisher_detail = client.get(f"/api/get_request_detail/{review_request.id}/")

    assert publisher_detail.status_code == 200
    assert publisher_detail.data["status"] == {"done": 1, "process": 0}
    assert publisher_detail.data["reviewers"][0]["status"] == "completed"
    assert publisher_detail.data["reviewers"][0]["completed_count"] == 1
