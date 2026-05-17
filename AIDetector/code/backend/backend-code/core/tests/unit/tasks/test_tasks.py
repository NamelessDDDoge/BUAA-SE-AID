"""core/tasks.py — compatibility wrappers"""
from unittest.mock import patch

import pytest

from core import tasks
from core.tests.factories import make_detection_task

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@patch("core.tasks.run_paper_detection_task")
def test_run_paper_detection_delegates_with_api_key(mock_runner):
    mock_runner.return_value = "done"
    out = tasks.run_paper_detection(123, api_key="sk-xx")
    mock_runner.assert_called_once_with(123, api_key="sk-xx")
    assert out == "done"


@patch("core.tasks.run_review_detection_task")
def test_run_review_detection_delegates(mock_runner):
    mock_runner.return_value = "rdone"
    out = tasks.run_review_detection(7)
    mock_runner.assert_called_once_with(7, api_key=None)
    assert out == "rdone"


@patch("core.tasks.generate_task_report")
def test_generate_report_for_task_fetches_task_and_calls_generator(mock_gen):
    task = make_detection_task()
    mock_gen.return_value = "report.pdf"
    out = tasks.generate_report_for_task(task.id)
    mock_gen.assert_called_once()
    args, _ = mock_gen.call_args
    assert args[0].id == task.id
    assert out == "report.pdf"


def test_generate_report_for_task_raises_for_unknown_task_id():
    from core.models import DetectionTask
    with pytest.raises(DetectionTask.DoesNotExist):
        tasks.generate_report_for_task(999999)
