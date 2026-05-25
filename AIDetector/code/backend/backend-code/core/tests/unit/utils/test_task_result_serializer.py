"""task_result_serializer status/progress helpers."""

import pytest

from core.models import DetectionResult
from core.tests.factories import make_detection_task, make_image_upload
from core.utils.task_result_serializer import build_task_progress, build_task_result_summary

pytestmark = pytest.mark.django_db


def test_build_task_result_summary_distinguishes_pending_and_in_progress():
    pending_task = make_detection_task(status="pending")
    running_task = make_detection_task(status="in_progress")

    assert build_task_result_summary(pending_task) == "排队中"
    assert build_task_result_summary(running_task) == "检测进行中"


def test_build_task_progress_counts_queued_and_running_results_separately():
    task = make_detection_task(status="in_progress")
    image_a = make_image_upload(detection_task=task)
    image_b = make_image_upload(detection_task=task)
    DetectionResult.objects.create(detection_task=task, image_upload=image_a, status="pending")
    DetectionResult.objects.create(detection_task=task, image_upload=image_b, status="in_progress")

    progress = build_task_progress(task)

    assert progress["queued_results"] == 1
    assert progress["in_progress_results"] == 1
    assert progress["pending_results"] == 2
