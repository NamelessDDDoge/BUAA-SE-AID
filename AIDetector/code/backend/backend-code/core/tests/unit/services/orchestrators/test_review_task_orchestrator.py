"""orchestrators/review_task_orchestrator — 复核请求构建 + 失败路径"""
import pytest

from core.services.orchestrators import review_task_orchestrator as orch
from core.tests.factories import (
    make_detection_task,
    make_file_management,
    make_user,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# ---------- _get_text_override ----------

def test_get_text_override_returns_empty_when_no_payload():
    task = make_detection_task(text_detection_results=None)
    assert orch._get_text_override(task) == ""


def test_get_text_override_returns_empty_for_non_dict_payload():
    task = make_detection_task(text_detection_results=[1, 2, 3])
    assert orch._get_text_override(task) == ""


def test_get_text_override_default_key_is_text_override():
    task = make_detection_task(text_detection_results={"text_override": "X"})
    assert orch._get_text_override(task) == "X"


def test_get_text_override_supports_custom_key():
    task = make_detection_task(
        text_detection_results={"paper_text_override": "P", "review_text_override": "R"},
    )
    assert orch._get_text_override(task, "paper_text_override") == "P"
    assert orch._get_text_override(task, "review_text_override") == "R"


def test_get_text_override_returns_empty_when_value_not_string():
    task = make_detection_task(text_detection_results={"text_override": [1]})
    assert orch._get_text_override(task) == ""


# ---------- _mark_review_task_failed ----------

def test_mark_review_task_failed_sets_status_and_completion_time():
    task = make_detection_task(task_type="review", status="in_progress")
    msg = orch._mark_review_task_failed(task, "boom-error")
    assert msg == "boom-error"
    task.refresh_from_db()
    assert task.status == "failed"
    assert task.error_message == "boom-error"
    assert task.completion_time is not None


# ---------- build_resource_review_placeholder: 校验 ----------

def test_build_resource_review_placeholder_requires_task_id():
    user = make_user()
    with pytest.raises(ValueError, match="task_id is required"):
        orch.build_resource_review_placeholder(user=user, task_id=None, reviewers=[1])


def test_build_resource_review_placeholder_requires_nonempty_reviewers():
    user = make_user()
    task = make_detection_task(user=user, task_type="paper", status="completed")
    with pytest.raises(ValueError, match="reviewers is required"):
        orch.build_resource_review_placeholder(user=user, task_id=task.id, reviewers=[])
    with pytest.raises(ValueError, match="reviewers is required"):
        orch.build_resource_review_placeholder(user=user, task_id=task.id, reviewers="not-list")


def test_build_resource_review_placeholder_selected_file_ids_must_be_list():
    user = make_user()
    task = make_detection_task(user=user, task_type="paper", status="completed")
    rev = make_user(organization=user.organization, role="reviewer")
    with pytest.raises(ValueError, match="selected_file_ids must be a list"):
        orch.build_resource_review_placeholder(
            user=user, task_id=task.id, reviewers=[rev.id], selected_file_ids="not-list",
        )


def test_build_resource_review_placeholder_task_not_found():
    user = make_user()
    with pytest.raises(FileNotFoundError, match="Detection task not found"):
        orch.build_resource_review_placeholder(
            user=user, task_id=999999, reviewers=[1],
        )


def test_build_resource_review_placeholder_rejects_image_task():
    user = make_user()
    task = make_detection_task(user=user, task_type="image", status="completed")
    rev = make_user(organization=user.organization, role="reviewer")
    with pytest.raises(ValueError, match="paper/review tasks"):
        orch.build_resource_review_placeholder(
            user=user, task_id=task.id, reviewers=[rev.id],
        )


def test_build_resource_review_placeholder_requires_completed_status():
    user = make_user()
    task = make_detection_task(user=user, task_type="paper", status="in_progress")
    rev = make_user(organization=user.organization, role="reviewer")
    with pytest.raises(ValueError, match="not completed yet"):
        orch.build_resource_review_placeholder(
            user=user, task_id=task.id, reviewers=[rev.id],
        )


def test_build_resource_review_placeholder_rejects_non_reviewer_id():
    user = make_user()
    task = make_detection_task(user=user, task_type="paper", status="completed")
    # 用 publisher 的 id 作为 "reviewer"，应被拒绝
    publisher = make_user(organization=user.organization, role="publisher")
    with pytest.raises(FileNotFoundError, match="reviewer IDs"):
        orch.build_resource_review_placeholder(
            user=user, task_id=task.id, reviewers=[publisher.id],
        )


def test_build_resource_review_placeholder_rejects_files_not_in_task():
    user = make_user()
    task = make_detection_task(user=user, task_type="paper", status="completed")
    rev = make_user(organization=user.organization, role="reviewer")
    foreign_file = make_file_management(user=user, resource_type="paper")
    with pytest.raises(ValueError, match="do not belong"):
        orch.build_resource_review_placeholder(
            user=user, task_id=task.id, reviewers=[rev.id],
            selected_file_ids=[foreign_file.id],
        )


def test_build_resource_review_placeholder_happy_path_returns_payload():
    user = make_user()
    task = make_detection_task(user=user, task_type="paper", status="completed")
    f = make_file_management(user=user, resource_type="paper")
    task.resource_files.add(f)
    rev1 = make_user(organization=user.organization, role="reviewer")
    rev2 = make_user(organization=user.organization, role="reviewer")

    payload = orch.build_resource_review_placeholder(
        user=user, task_id=task.id, reviewers=[rev1.id, rev2.id], reason="check please",
    )
    assert payload["task_id"] == task.id
    assert payload["task_type"] == "paper"
    assert payload["reason"] == "check please"
    assert payload["placeholder_request_id"].startswith("RR-")
    assert len(payload["reviewers"]) == 2
    assert {r["id"] for r in payload["reviewers"]} == {rev1.id, rev2.id}
    assert len(payload["selected_files"]) == 1
    assert payload["selected_files"][0]["file_id"] == f.id


def test_build_resource_review_placeholder_uses_default_reason_when_blank():
    user = make_user()
    task = make_detection_task(user=user, task_type="paper", status="completed")
    rev = make_user(organization=user.organization, role="reviewer")
    payload = orch.build_resource_review_placeholder(
        user=user, task_id=task.id, reviewers=[rev.id], reason="   ",
    )
    assert payload["reason"] == "No reason provided"


# ---------- run_review_detection_task: 失败路径 ----------

def test_run_review_detection_task_fails_when_files_missing():
    task = make_detection_task(task_type="review", status="pending")
    msg = orch.run_review_detection_task(task.id)
    assert "review_paper and review_file" in msg
    task.refresh_from_db()
    assert task.status == "failed"


def test_run_review_detection_task_fails_when_only_paper_present():
    task = make_detection_task(task_type="review", status="pending")
    f = make_file_management(user=task.user, resource_type="review_paper")
    task.resource_files.add(f)
    msg = orch.run_review_detection_task(task.id)
    assert "review_paper and review_file" in msg


def test_run_review_detection_task_fails_when_file_path_does_not_exist():
    task = make_detection_task(task_type="review", status="pending")
    paper = make_file_management(user=task.user, resource_type="review_paper", stored_path="missing-paper.pdf")
    review = make_file_management(user=task.user, resource_type="review_file", stored_path="missing-review.pdf")
    task.resource_files.add(paper, review)
    msg = orch.run_review_detection_task(task.id)
    assert "file path does not exist" in msg


# ---------- _build_document_from_text ----------

def test_build_document_from_text_returns_required_keys():
    out = orch._build_document_from_text("Abstract: Some intro\n\nBody paragraph one.\n\nBody paragraph two.")
    assert "text_content" in out
    assert "paragraphs" in out
    assert "sections" in out
    assert "references" in out
    assert "segments" in out
    assert out["text_content"].startswith("Abstract")
