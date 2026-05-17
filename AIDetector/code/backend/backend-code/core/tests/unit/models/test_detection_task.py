"""5.7 DetectionTask 表"""
import pytest

from core.models import DetectionTask
from core.tests.factories import make_detection_task, make_file_management, make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_str_includes_task_id_and_username():
    user = make_user(username="charlie")
    t = make_detection_task(user=user)
    rendered = str(t)
    assert f"Task {t.id}" in rendered
    assert "charlie" in rendered


def test_default_status_is_pending():
    t = make_detection_task()
    assert t.status == "pending"


def test_default_task_type_is_image():
    t = make_detection_task()
    assert t.task_type == "image"


def test_if_use_llm_defaults_false():
    t = make_detection_task()
    assert t.if_use_llm is False


def test_method_switches_stored_as_json():
    switches = {"ela": True, "exif": False, "urn_coarse_v2": True}
    t = make_detection_task(method_switches=switches)
    t.refresh_from_db()
    assert t.method_switches == switches


def test_text_detection_results_stored_as_json_list():
    payload = [{"segment_index": 0, "label": "ai", "probability": 0.92}]
    t = make_detection_task(text_detection_results=payload)
    t.refresh_from_db()
    assert t.text_detection_results == payload


def test_resource_files_can_be_attached_via_m2m():
    user = make_user()
    f1 = make_file_management(user=user, resource_type="paper")
    f2 = make_file_management(user=user, resource_type="review_paper")
    t = make_detection_task(user=user, task_type="paper")
    t.resource_files.set([f1, f2])
    assert t.resource_files.count() == 2
    assert set(t.resource_files.values_list("id", flat=True)) == {f1.id, f2.id}


def test_task_type_accepts_all_three_choices():
    user = make_user()
    for tt in ("image", "paper", "review"):
        t = DetectionTask.objects.create(
            user=user,
            organization=user.organization,
            task_name=f"t-{tt}",
            task_type=tt,
        )
        assert t.task_type == tt


def test_status_accepts_failed_state():
    t = make_detection_task(status="failed", error_message="boom")
    t.refresh_from_db()
    assert t.status == "failed"
    assert t.error_message == "boom"
