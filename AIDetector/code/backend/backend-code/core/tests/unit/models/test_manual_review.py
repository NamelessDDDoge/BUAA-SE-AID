"""5.14 ManualReview 表"""
import pytest
from django.test import override_settings

from core.tests.factories import (
    make_image_upload,
    make_manual_review,
    make_review_request,
    make_user,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@override_settings(MEDIA_ROOT="/tmp/test-media-manual-review")
def test_default_status_is_undo():
    mr = make_manual_review()
    assert mr.status == "undo"


@override_settings(MEDIA_ROOT="/tmp/test-media-manual-review")
def test_str_includes_reviewer_username():
    user = make_user(username="elsa", role="reviewer")
    rr = make_review_request()
    mr = make_manual_review(review_request=rr, reviewer=user)
    rendered = str(mr)
    assert "elsa" in rendered


@override_settings(MEDIA_ROOT="/tmp/test-media-manual-review")
def test_status_transitions_to_completed():
    mr = make_manual_review()
    mr.status = "completed"
    mr.save()
    mr.refresh_from_db()
    assert mr.status == "completed"


@override_settings(MEDIA_ROOT="/tmp/test-media-manual-review")
def test_imgs_can_attach_multiple_image_uploads():
    rr = make_review_request()
    mr = make_manual_review(review_request=rr)
    task = rr.detection_result.detection_task
    img1 = make_image_upload(detection_task=task)
    img2 = make_image_upload(detection_task=task)
    mr.imgs.set([img1, img2])
    assert mr.imgs.count() == 2
