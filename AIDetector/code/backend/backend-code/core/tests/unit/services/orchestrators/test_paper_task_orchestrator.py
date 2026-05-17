"""orchestrators/paper_task_orchestrator — 纯函数 + 失败路径

完整流程的集成测试见 core/tests/integration/api/detection/test_resource_task_flow.py。
这里只覆盖辅助函数：_mark_task_failed / _paper_image_detection_enabled / _get_text_override。
"""
import pytest

from core.services.orchestrators import paper_task_orchestrator as orch
from core.tests.factories import make_detection_task

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# ---------- _paper_image_detection_enabled ----------

def test_image_detection_enabled_true_by_default():
    task = make_detection_task(task_type="paper", method_switches=None)
    assert orch._paper_image_detection_enabled(task) is True


def test_image_detection_enabled_false_when_extract_images_off():
    task = make_detection_task(
        task_type="paper",
        method_switches={"__paper_extract_images__": False, "ela": True},
    )
    assert orch._paper_image_detection_enabled(task) is False


def test_image_detection_enabled_false_when_all_image_methods_off():
    task = make_detection_task(
        task_type="paper",
        method_switches={
            "__paper_extract_images__": True,
            "ela": False,
            "exif": False,
            "cmd": False,
        },
    )
    assert orch._paper_image_detection_enabled(task) is False


def test_image_detection_enabled_true_when_extract_on_and_any_method_on():
    task = make_detection_task(
        task_type="paper",
        method_switches={
            "__paper_extract_images__": True,
            "ela": True,
            "exif": False,
        },
    )
    assert orch._paper_image_detection_enabled(task) is True


def test_image_detection_enabled_with_urn_method_on():
    task = make_detection_task(
        task_type="paper",
        method_switches={
            "__paper_extract_images__": True,
            "ela": False,
            "urn_coarse_v2": True,
        },
    )
    assert orch._paper_image_detection_enabled(task) is True


# ---------- _mark_task_failed ----------

def test_mark_task_failed_updates_status_and_returns_message():
    task = make_detection_task(task_type="paper", status="in_progress")
    msg = orch._mark_task_failed(task, "boom")
    assert msg == "boom"
    task.refresh_from_db()
    assert task.status == "failed"
    assert task.error_message == "boom"
    assert task.completion_time is not None


# ---------- _get_text_override ----------

def test_get_text_override_returns_empty_when_no_text_detection_results():
    task = make_detection_task(task_type="paper", text_detection_results=None)
    assert orch._get_text_override(task) == ""


def test_get_text_override_returns_empty_when_results_not_dict():
    task = make_detection_task(task_type="paper", text_detection_results=["list"])
    assert orch._get_text_override(task) == ""


def test_get_text_override_returns_empty_when_text_override_missing():
    task = make_detection_task(
        task_type="paper", text_detection_results={"other_key": "val"},
    )
    assert orch._get_text_override(task) == ""


def test_get_text_override_returns_string_when_present():
    task = make_detection_task(
        task_type="paper",
        text_detection_results={"text_override": "用户修改的论文文本"},
    )
    assert orch._get_text_override(task) == "用户修改的论文文本"


def test_get_text_override_returns_empty_when_text_override_not_string():
    task = make_detection_task(
        task_type="paper", text_detection_results={"text_override": 42},
    )
    assert orch._get_text_override(task) == ""


# ---------- run_paper_detection_task: 失败路径 ----------

def test_run_paper_detection_task_fails_when_no_paper_file():
    task = make_detection_task(task_type="paper")  # 没附加 resource_files
    msg = orch.run_paper_detection_task(task.id)
    assert msg == "No paper resource file found"
    task.refresh_from_db()
    assert task.status == "failed"


def test_run_paper_detection_task_fails_when_file_missing_on_disk(tmp_path):
    from core.tests.factories import make_file_management
    task = make_detection_task(task_type="paper")
    f = make_file_management(
        user=task.user,
        resource_type="paper",
        stored_path="does/not/exist.pdf",
    )
    task.resource_files.add(f)
    msg = orch.run_paper_detection_task(task.id)
    assert msg == "Paper file path does not exist"
    task.refresh_from_db()
    assert task.status == "failed"
