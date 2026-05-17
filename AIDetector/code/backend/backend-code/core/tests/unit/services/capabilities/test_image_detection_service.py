"""capabilities/image_detection_service — 仅是 execute_detection_task 的薄壳"""
from unittest.mock import patch

import pytest

from core.services.capabilities.image_detection_service import run_image_detection_task

pytestmark = pytest.mark.unit


@patch("core.services.capabilities.image_detection_service.execute_detection_task")
def test_run_image_detection_task_delegates_to_execute(mock_exec):
    mock_exec.return_value = "result-sentinel"
    out = run_image_detection_task(detection_task="TASK", image_uploads=["i1", "i2"])
    mock_exec.assert_called_once_with("TASK", ["i1", "i2"])
    assert out == "result-sentinel"


@patch("core.services.capabilities.image_detection_service.execute_detection_task")
def test_run_image_detection_task_passes_through_exception(mock_exec):
    mock_exec.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError, match="boom"):
        run_image_detection_task(detection_task="T", image_uploads=[])
