"""5.8 ImageUpload 表"""
import pytest
from django.test import override_settings

from core.tests.factories import make_image_upload, make_detection_task, make_file_management

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@override_settings(MEDIA_ROOT="/tmp/test-media-image-upload")
def test_str_contains_file_name():
    f = make_file_management(file_name="figure-1.png")
    img = make_image_upload(file_management=f)
    rendered = str(img)
    assert "figure-1.png" in rendered


@override_settings(MEDIA_ROOT="/tmp/test-media-image-upload")
def test_defaults_for_isDetect_isReview_isFake_extracted_from_pdf():
    img = make_image_upload()
    assert img.isDetect is False
    assert img.isReview is False
    assert img.isFake is False
    assert img.extracted_from_pdf is False
    assert img.page_number is None


@override_settings(MEDIA_ROOT="/tmp/test-media-image-upload")
def test_can_mark_extracted_from_pdf_with_page_number():
    img = make_image_upload(extracted_from_pdf=True, page_number=5)
    img.refresh_from_db()
    assert img.extracted_from_pdf is True
    assert img.page_number == 5


@override_settings(MEDIA_ROOT="/tmp/test-media-image-upload")
def test_detection_task_link_optional_but_file_management_required():
    task = make_detection_task()
    img = make_image_upload(detection_task=task)
    assert img.detection_task_id == task.id
    assert img.file_management is not None
