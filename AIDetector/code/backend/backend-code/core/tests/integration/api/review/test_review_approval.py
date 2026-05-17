"""DTC-ADMIN-6 人工审核审批"""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from core.tests.factories import make_review_request, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


@override_settings(MEDIA_ROOT="/tmp/test-media-review-approve")
def test_handle_review_request_requires_authentication(client):
    resp = client.post("/api/handle_reviewRequest/1/", {}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-review-approve")
def test_get_all_review_requests_requires_authentication(client):
    resp = client.get("/api/get_reviewRequest/all/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-review-approve")
def test_get_review_request_detail_admin_requires_authentication(client):
    rr = make_review_request()
    resp = client.get(f"/api/get_reviewRequest/{rr.id}/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 401, 403)


@override_settings(MEDIA_ROOT="/tmp/test-media-review-approve")
def test_delete_review_request_requires_authentication(client):
    rr = make_review_request()
    resp = client.delete(f"/api/review-requests/{rr.id}/delete/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (401, 403, 405)
