"""5.13 ReviewRequest 表"""
import pytest
from django.test import override_settings

from core.tests.factories import (
    make_image_upload,
    make_review_request,
    make_user,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@override_settings(MEDIA_ROOT="/tmp/test-media-review-request")
def test_default_status1_and_status2_pending():
    rr = make_review_request()
    assert rr.status1 == "pending"
    assert rr.status2 == "pending"


@override_settings(MEDIA_ROOT="/tmp/test-media-review-request")
def test_str_contains_detection_result_id_and_username():
    user = make_user(username="dora")
    rr = make_review_request(user=user)
    rendered = str(rr)
    assert str(rr.detection_result.id) in rendered
    assert "dora" in rendered


@override_settings(MEDIA_ROOT="/tmp/test-media-review-request")
def test_status1_lifecycle_transitions():
    rr = make_review_request()
    for s in ("in_progress", "completed"):
        rr.status1 = s
        rr.save()
        rr.refresh_from_db()
        assert rr.status1 == s


@override_settings(MEDIA_ROOT="/tmp/test-media-review-request")
def test_status2_lifecycle_transitions():
    rr = make_review_request()
    for s in ("accepted", "refused"):
        rr.status2 = s
        rr.save()
        rr.refresh_from_db()
        assert rr.status2 == s


@override_settings(MEDIA_ROOT="/tmp/test-media-review-request")
def test_imgs_m2m_can_attach_multiple_image_uploads():
    rr = make_review_request()
    img1 = make_image_upload(detection_task=rr.detection_result.detection_task)
    img2 = make_image_upload(detection_task=rr.detection_result.detection_task)
    rr.imgs.set([img1, img2])
    assert rr.imgs.count() == 2


@override_settings(MEDIA_ROOT="/tmp/test-media-review-request")
def test_reviewers_m2m_can_attach_multiple_users():
    rr = make_review_request()
    rev1 = make_user(organization=rr.organization, role="reviewer")
    rev2 = make_user(organization=rr.organization, role="reviewer")
    rr.reviewers.set([rev1, rev2])
    assert rr.reviewers.count() == 2
