"""orchestrators/resource_task_orchestrator — 论文/Review 任务创建参数校验

集成测试见 core/tests/integration/api/detection/test_resource_task_flow.py。
这里只覆盖参数校验、_normalize_resource_method_switches、_get_resource_task_runner。
"""
from unittest.mock import MagicMock

import pytest

from core.services.orchestrators import resource_task_orchestrator as orch
from core.tests.factories import make_file_management, make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# ---------- _normalize_resource_method_switches ----------

def test_normalize_method_switches_passes_through_none():
    assert orch._normalize_resource_method_switches(None) is None


def test_normalize_method_switches_coerces_keys_and_values():
    out = orch._normalize_resource_method_switches({"llm": 1, 5: ""})
    assert out == {"llm": True, "5": False}


def test_normalize_method_switches_rejects_non_dict():
    with pytest.raises(ValueError, match="must be an object"):
        orch._normalize_resource_method_switches([("a", True)])


# ---------- _get_resource_task_runner ----------

def test_get_resource_task_runner_paper():
    from core.services.orchestrators.paper_task_orchestrator import run_paper_detection_task
    assert orch._get_resource_task_runner("paper") is run_paper_detection_task


def test_get_resource_task_runner_review():
    from core.services.orchestrators.review_task_orchestrator import run_review_detection_task
    assert orch._get_resource_task_runner("review") is run_review_detection_task


def test_get_resource_task_runner_unsupported_raises():
    with pytest.raises(ValueError, match="Unsupported"):
        orch._get_resource_task_runner("image")


# ---------- create_resource_detection_task: 参数校验 ----------

def test_create_resource_task_rejects_unknown_task_type():
    user = make_user()
    with pytest.raises(ValueError, match="paper or review"):
        orch.create_resource_detection_task(user=user, task_type="image", file_ids=[1])


def test_create_resource_task_rejects_empty_file_ids():
    user = make_user()
    with pytest.raises(ValueError, match="file_ids is required"):
        orch.create_resource_detection_task(user=user, task_type="paper", file_ids=[])


def test_create_resource_task_rejects_non_list_file_ids():
    user = make_user()
    with pytest.raises(ValueError, match="file_ids is required"):
        orch.create_resource_detection_task(user=user, task_type="paper", file_ids="not-list")


def test_create_resource_task_rejects_foreign_file():
    user = make_user()
    other = make_user()
    foreign_file = make_file_management(user=other, resource_type="paper")
    with pytest.raises(FileNotFoundError, match="do not belong"):
        orch.create_resource_detection_task(
            user=user, task_type="paper", file_ids=[foreign_file.id],
        )


def test_create_paper_task_rejects_non_paper_file():
    user = make_user()
    f = make_file_management(user=user, resource_type="image")
    with pytest.raises(ValueError, match="paper resource files"):
        orch.create_resource_detection_task(
            user=user, task_type="paper", file_ids=[f.id],
        )


def test_create_review_task_requires_both_paper_and_review_file():
    user = make_user()
    paper = make_file_management(user=user, resource_type="review_paper")
    with pytest.raises(ValueError, match="review_paper and review_file"):
        orch.create_resource_detection_task(
            user=user, task_type="review", file_ids=[paper.id],
        )


def test_create_review_task_requires_link_between_paper_and_review_file():
    user = make_user()
    paper = make_file_management(user=user, resource_type="review_paper")
    # review_file 不指向上面的 paper
    rev = make_file_management(user=user, resource_type="review_file")
    with pytest.raises(ValueError, match="not correctly linked"):
        orch.create_resource_detection_task(
            user=user, task_type="review", file_ids=[paper.id, rev.id],
        )


# ---------- create_resource_detection_task: 成功路径 ----------

def test_create_paper_task_happy_path_with_default_name():
    user = make_user()
    f = make_file_management(user=user, resource_type="paper")
    task, files = orch.create_resource_detection_task(
        user=user, task_type="paper", file_ids=[f.id],
    )
    assert task.task_type == "paper"
    assert task.status == "pending"  # 没传 async_task_starter
    assert "论文检测" in task.task_name
    assert task.resource_files.count() == 1
    assert files[0].id == f.id


def test_create_review_task_happy_path():
    user = make_user()
    paper = make_file_management(user=user, resource_type="review_paper")
    rev = make_file_management(user=user, resource_type="review_file", linked_file=paper)
    task, files = orch.create_resource_detection_task(
        user=user, task_type="review", file_ids=[paper.id, rev.id],
    )
    assert task.task_type == "review"
    assert "Review检测" in task.task_name
    assert task.resource_files.count() == 2


def test_create_paper_task_with_extract_images_flag_persists_switch():
    user = make_user()
    f = make_file_management(user=user, resource_type="paper")
    task, _ = orch.create_resource_detection_task(
        user=user, task_type="paper", file_ids=[f.id], extract_images=False,
    )
    assert task.method_switches["__paper_extract_images__"] is False


def test_create_paper_task_with_text_override_persisted():
    user = make_user()
    f = make_file_management(user=user, resource_type="paper")
    task, _ = orch.create_resource_detection_task(
        user=user, task_type="paper", file_ids=[f.id], text_override="覆盖的论文文本",
    )
    assert task.text_detection_results["paper_text_override"] == "覆盖的论文文本"


def test_create_review_task_with_dual_overrides_persisted():
    user = make_user()
    paper = make_file_management(user=user, resource_type="review_paper")
    rev = make_file_management(user=user, resource_type="review_file", linked_file=paper)
    task, _ = orch.create_resource_detection_task(
        user=user, task_type="review", file_ids=[paper.id, rev.id],
        paper_text_override="P", review_text_override="R",
    )
    assert task.text_detection_results["paper_text_override"] == "P"
    assert task.text_detection_results["review_text_override"] == "R"


def test_create_task_with_async_starter_marks_pending_until_worker_starts():
    user = make_user()
    f = make_file_management(user=user, resource_type="paper")
    starter = MagicMock()
    commit_hook = lambda fn: fn()
    task, _ = orch.create_resource_detection_task(
        user=user, task_type="paper", file_ids=[f.id],
        async_task_starter=starter, on_commit=commit_hook,
    )
    assert task.status == "pending"
    starter.assert_called_once_with("paper", task.id, None)


def test_create_task_method_switches_with_llm_forces_if_use_llm():
    user = make_user()
    f = make_file_management(user=user, resource_type="paper")
    task, _ = orch.create_resource_detection_task(
        user=user, task_type="paper", file_ids=[f.id],
        if_use_llm=False, method_switches={"llm": True},
    )
    assert task.if_use_llm is True


# ---------- run_resource_detection_task_async ----------

def test_run_resource_detection_task_async_marks_failed_on_exception(monkeypatch):
    from core.tests.factories import make_detection_task
    task = make_detection_task(task_type="paper", status="pending")

    def boom(_task_id, **_kw):
        raise RuntimeError("paper crashed")
    monkeypatch.setattr(orch, "run_paper_detection_task", boom)

    orch.run_resource_detection_task_async("paper", task.id)
    task.refresh_from_db()
    assert task.status == "failed"
    assert "paper crashed" in task.error_message


def test_run_resource_detection_task_async_dispatches_to_correct_runner(monkeypatch):
    from core.tests.factories import make_detection_task
    task = make_detection_task(task_type="review", status="pending")
    review_runner = MagicMock()
    monkeypatch.setattr(orch, "run_review_detection_task", review_runner)

    orch.run_resource_detection_task_async("review", task.id, api_key="k1")
    review_runner.assert_called_once_with(task.id, api_key="k1")


def test_run_resource_detection_task_async_skips_non_pending_task(monkeypatch):
    from core.tests.factories import make_detection_task
    task = make_detection_task(task_type="paper", status="completed")
    paper_runner = MagicMock()
    monkeypatch.setattr(orch, "run_paper_detection_task", paper_runner)

    orch.run_resource_detection_task_async("paper", task.id)

    task.refresh_from_db()
    assert task.status == "completed"
    paper_runner.assert_not_called()
