"""5.11 DetectionResult 表"""
import pytest
from django.test import override_settings

from core.tests.factories import make_detection_result, make_review_request

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@override_settings(MEDIA_ROOT="/tmp/test-media-detection-result")
def test_str_contains_image_upload_id():
    dr = make_detection_result()
    assert str(dr.image_upload.id) in str(dr)


@override_settings(MEDIA_ROOT="/tmp/test-media-detection-result")
def test_default_status_is_in_progress():
    dr = make_detection_result()
    assert dr.status == "in_progress"


@override_settings(MEDIA_ROOT="/tmp/test-media-detection-result")
def test_initial_is_fake_and_confidence_are_null():
    dr = make_detection_result()
    assert dr.is_fake is None
    assert dr.confidence_score is None
    assert dr.detection_time is None
    assert dr.llm_judgment is None
    assert dr.exif_photoshop is None
    assert dr.exif_time_modified is None


@override_settings(MEDIA_ROOT="/tmp/test-media-detection-result")
def test_is_under_review_defaults_false():
    dr = make_detection_result()
    assert dr.is_under_review is False
    assert dr.review_request is None


@override_settings(MEDIA_ROOT="/tmp/test-media-detection-result")
def test_one_to_one_review_request_can_be_attached():
    dr = make_detection_result()
    rr = make_review_request(detection_result=dr)
    dr.review_request = rr
    dr.is_under_review = True
    dr.save()
    dr.refresh_from_db()
    assert dr.review_request_id == rr.id
    assert dr.is_under_review is True


@override_settings(MEDIA_ROOT="/tmp/test-media-detection-result")
def test_status_can_be_set_to_completed_and_failed():
    dr = make_detection_result(status="completed")
    assert dr.status == "completed"
    dr.status = "failed"
    dr.save()
    dr.refresh_from_db()
    assert dr.status == "failed"
