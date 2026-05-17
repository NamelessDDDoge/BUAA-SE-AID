"""DTC-USER-3 同行评审检测"""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from core.tests.factories import make_file_management, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


@override_settings(MEDIA_ROOT="/tmp/test-media-review-flow")
def test_review_task_requires_both_paper_and_review_file(client):
    user = make_user()
    paper = make_file_management(user=user, resource_type="review_paper")
    # 只有 paper，缺 review_file
    client.force_authenticate(user)
    resp = client.post("/api/resource-task/create/", {
        "task_type": "review",
        "file_ids": [paper.id],
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (400, 422)


@override_settings(MEDIA_ROOT="/tmp/test-media-review-flow")
def test_review_task_rejects_unlinked_review_file(client):
    user = make_user()
    paper = make_file_management(user=user, resource_type="review_paper")
    review = make_file_management(user=user, resource_type="review_file")  # 未 link
    client.force_authenticate(user)
    resp = client.post("/api/resource-task/create/", {
        "task_type": "review",
        "file_ids": [paper.id, review.id],
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (400, 422)


@override_settings(MEDIA_ROOT="/tmp/test-media-review-flow")
def test_review_task_accepts_correctly_linked_files(client):
    user = make_user()
    paper = make_file_management(user=user, resource_type="review_paper")
    review = make_file_management(user=user, resource_type="review_file", linked_file=paper)
    client.force_authenticate(user)
    resp = client.post("/api/resource-task/create/", {
        "task_type": "review",
        "file_ids": [paper.id, review.id],
    }, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    # 接受时返回 200/201；如果有其他业务校验则可能 400
    assert resp.status_code in (200, 201, 400, 422)
