"""ResourceReviewRequest / ResourceManualReview

代码里实际存在但《概要设计》5.x 列表未列出的模型。
对应论文/同行评审"资源类"任务的人工复核请求与执行（DTC-USER-4 论文链路）。
"""
import pytest
from django.db import IntegrityError

from core.models import ResourceManualReview, ResourceReviewRequest
from core.tests.factories import make_detection_task, make_file_management, make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _make_request(**overrides):
    task = overrides.pop("detection_task", None) or make_detection_task(task_type="paper")
    user = overrides.pop("user", None) or task.user
    defaults = dict(
        detection_task=task,
        task_type="paper",
        user=user,
        organization=user.organization,
    )
    defaults.update(overrides)
    return ResourceReviewRequest.objects.create(**defaults)


def test_default_status1_status2_pending():
    rr = _make_request()
    assert rr.status1 == "pending"
    assert rr.status2 == "pending"


def test_default_reason_and_check_reason_are_empty_strings():
    rr = _make_request()
    assert rr.reason == ""
    assert rr.check_reason == ""


def test_str_contains_task_id():
    rr = _make_request()
    assert str(rr.detection_task_id) in str(rr)


def test_task_type_accepts_paper_and_review():
    for tt in ("paper", "review"):
        task = make_detection_task(task_type=tt)
        rr = _make_request(detection_task=task, task_type=tt)
        assert rr.task_type == tt


def test_selected_files_m2m():
    user = make_user()
    task = make_detection_task(task_type="paper", user=user)
    rr = _make_request(detection_task=task, user=user)
    f1 = make_file_management(user=user, resource_type="paper")
    f2 = make_file_management(user=user, resource_type="review_paper")
    rr.selected_files.set([f1, f2])
    assert rr.selected_files.count() == 2


def test_manual_review_unique_per_request_and_reviewer():
    rr = _make_request()
    reviewer = make_user(organization=rr.organization, role="reviewer")
    ResourceManualReview.objects.create(review_request=rr, reviewer=reviewer)
    with pytest.raises(IntegrityError):
        ResourceManualReview.objects.create(review_request=rr, reviewer=reviewer)


def test_manual_review_default_status_undo():
    rr = _make_request()
    reviewer = make_user(organization=rr.organization, role="reviewer")
    mr = ResourceManualReview.objects.create(review_request=rr, reviewer=reviewer)
    assert mr.status == "undo"
    assert mr.conclusion == ""
    assert mr.result_payload is None


def test_manual_review_result_payload_json_round_trip():
    rr = _make_request()
    reviewer = make_user(organization=rr.organization, role="reviewer")
    payload = {"verdict": "ai-generated", "confidence": 0.81, "tags": ["paragraph-3"]}
    mr = ResourceManualReview.objects.create(
        review_request=rr, reviewer=reviewer, result_payload=payload,
    )
    mr.refresh_from_db()
    assert mr.result_payload == payload
