"""
Task 4: Review task creation validation.

Covers:
- only review_paper supplied → 400
- only review_file supplied → 400
- review_file present but linked_file not set → 400
- review_file linked to wrong paper → 400
- two review_papers (not exactly one) → 400
- correctly linked pair → 200/201
- foreign files (other user) → 400/404
"""
import pytest
from unittest.mock import patch
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import DetectionTask
from core.tests.factories import make_user, make_file_management

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

CREATE_URL = "/api/resource-task/create/"


@pytest.fixture
def client():
    return APIClient()


# -------------------------------------------------------------------
# T4-A: only review_paper, no review_file → 400
# -------------------------------------------------------------------
def test_review_task_only_paper_no_review_file(client, tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        user = make_user(role="publisher")
        paper = make_file_management(user=user, resource_type="review_paper")
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [paper.id],
        }, format="json")

        assert resp.status_code == 400, (
            f"Expected 400 when review_file is missing, got {resp.status_code}: {resp.data}"
        )
        assert not DetectionTask.objects.filter(user=user).exists()


# -------------------------------------------------------------------
# T4-B: only review_file, no review_paper → 400
# -------------------------------------------------------------------
def test_review_task_only_review_file_no_paper(client, tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        user = make_user(role="publisher")
        review = make_file_management(user=user, resource_type="review_file")
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [review.id],
        }, format="json")

        assert resp.status_code == 400, (
            f"Expected 400 when review_paper is missing, got {resp.status_code}: {resp.data}"
        )
        assert not DetectionTask.objects.filter(user=user).exists()


# -------------------------------------------------------------------
# T4-C: review_file not linked to any paper → 400
# -------------------------------------------------------------------
def test_review_task_unlinked_review_file_rejected(client, tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        user = make_user(role="publisher")
        paper = make_file_management(user=user, resource_type="review_paper")
        review = make_file_management(user=user, resource_type="review_file")
        # linked_file is NOT set — review.linked_file is None
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [paper.id, review.id],
        }, format="json")

        assert resp.status_code == 400, (
            f"Expected 400 when review_file has no linked_file, got {resp.status_code}: {resp.data}"
        )
        msg = str(resp.data.get("message", "")).lower()
        assert "link" in msg or "review" in msg or "paper" in msg, (
            f"Error message should mention linking issue: {resp.data}"
        )
        assert not DetectionTask.objects.filter(user=user).exists()


# -------------------------------------------------------------------
# T4-D: review_file linked to a DIFFERENT paper (not in file_ids) → 400
# -------------------------------------------------------------------
def test_review_task_review_file_linked_to_wrong_paper(client, tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        user = make_user(role="publisher")
        paper_a = make_file_management(user=user, resource_type="review_paper")
        paper_b = make_file_management(user=user, resource_type="review_paper")
        # review is linked to paper_b, but we submit paper_a + review
        review = make_file_management(user=user, resource_type="review_file",
                                       linked_file=paper_b)
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [paper_a.id, review.id],
        }, format="json")

        assert resp.status_code == 400, (
            f"Expected 400 when review_file linked to wrong paper, got {resp.status_code}: {resp.data}"
        )
        assert not DetectionTask.objects.filter(user=user).exists()


# -------------------------------------------------------------------
# T4-E: two review_papers submitted (orchestrator requires exactly one) → 400
# -------------------------------------------------------------------
def test_review_task_rejects_two_review_papers(client, tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        user = make_user(role="publisher")
        paper_a = make_file_management(user=user, resource_type="review_paper")
        paper_b = make_file_management(user=user, resource_type="review_paper")
        review = make_file_management(user=user, resource_type="review_file",
                                       linked_file=paper_a)
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [paper_a.id, paper_b.id, review.id],
        }, format="json")

        assert resp.status_code == 400, (
            f"Expected 400 when two review_papers submitted, got {resp.status_code}: {resp.data}"
        )


# -------------------------------------------------------------------
# T4-F: correctly linked files → 200/201 and task created
# -------------------------------------------------------------------
def test_review_task_correctly_linked_files_accepted(client, tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        user = make_user(role="publisher")
        paper = make_file_management(user=user, resource_type="review_paper")
        review = make_file_management(user=user, resource_type="review_file",
                                       linked_file=paper)
        client.force_authenticate(user)

        # Patch async runner to prevent actual task execution (no files on disk)
        with patch(
            "core.views.views_dectection.start_resource_detection_task_thread"
        ):
            resp = client.post(CREATE_URL, {
                "task_type": "review",
                "file_ids": [paper.id, review.id],
                "task_name": "Valid review task",
            }, format="json")

        assert resp.status_code in (200, 201), (
            f"Expected 200/201 for valid review task, got {resp.status_code}: {resp.data}"
        )
        assert resp.data.get("task_id") is not None
        assert DetectionTask.objects.filter(user=user, task_type="review").exists()


# -------------------------------------------------------------------
# T4-G: foreign review_paper (other user) → 400/404
# -------------------------------------------------------------------
def test_review_task_rejects_foreign_review_paper(client, tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        user = make_user(role="publisher")
        other = make_user(role="publisher")
        foreign_paper = make_file_management(user=other, resource_type="review_paper")
        review = make_file_management(user=user, resource_type="review_file",
                                       linked_file=foreign_paper)
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [foreign_paper.id, review.id],
        }, format="json")

        assert resp.status_code in (400, 404), (
            f"Expected 400 or 404 for foreign paper, got {resp.status_code}: {resp.data}"
        )
        assert not DetectionTask.objects.filter(user=user).exists()


"""
Task 5: Review detection complete chain — fast tier.
"""
import os
import pytest
from unittest.mock import patch
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import DetectionTask
from core.services.orchestrators.resource_task_orchestrator import run_resource_detection_task_async
from core.tests.factories import make_user, make_file_management

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

CREATE_URL = "/api/resource-task/create/"
RESULTS_URL = "/api/paper-results/{}/"

_PAPER_TEXT = (
    "Abstract\n\nThis paper proposes a new method for detecting AI-generated text.\n\n"
    "Introduction\n\nLarge language models have made forgery detection harder.\n\n"
    "Conclusion\n\nOur approach outperforms baselines.\n"
)

_REVIEW_TEXT = (
    "Summary\n\nThe paper presents interesting ideas.\n\n"
    "Strengths\n\nThe methodology is sound.\n\n"
    "Weaknesses\n\nThe evaluation is limited.\n"
)

FAKE_REVIEW_ANALYSIS = {
    "overall": {
        "template_like_level": "low",
        "wrongness_level": "low",
        "relevance_level": "high",
        "summary": "Genuine review.",
        "key_findings": ["Sound methodology"],
        "suggestions": [],
    },
    "paragraph_results": [
        {
            "review_paragraph_index": 0,
            "paper_paragraph_index": 0,
            "template_like_level": "low",
            "wrongness_level": "low",
            "relevance_score": 0.85,
            "relevance_level": "high",
            "explanation": "Review references abstract section correctly.",
        }
    ],
}


def _write_file(media_root: str, rel_path: str, content: str) -> str:
    full = os.path.join(media_root, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return rel_path


@patch(
    "core.services.capabilities.review_analysis_service.analyze_review_text",
    return_value=FAKE_REVIEW_ANALYSIS,
)
@patch(
    "core.views.views_dectection.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda f: f())
def test_review_detection_complete_chain(mock_on_commit, mock_starter, mock_analyze, tmp_path):
    """
    Full happy-path for review detection:
    - correctly linked paper + review_file
    - mock analyze_review_text
    - sync execution
    - task.status == 'completed'
    - GET /api/paper-results/<task_id>/ returns paragraph_results
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")

        paper_stored = _write_file(tmp_media, "review/paper.txt", _PAPER_TEXT)
        review_stored = _write_file(tmp_media, "review/review.txt", _REVIEW_TEXT)

        paper_file = make_file_management(
            user=user, resource_type="review_paper",
            stored_path=paper_stored, file_name="paper.txt",
        )
        review_file = make_file_management(
            user=user, resource_type="review_file",
            stored_path=review_stored, file_name="review.txt",
            linked_file=paper_file,
        )

        client = APIClient()
        client.force_authenticate(user)

        create_resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [paper_file.id, review_file.id],
            "task_name": "Fast-tier review test",
        }, format="json")

        assert create_resp.status_code in (200, 201), (
            f"Create failed: {create_resp.status_code} {create_resp.data}"
        )
        task_id = create_resp.data["task_id"]

        task = DetectionTask.objects.get(id=task_id)
        assert task.status == "completed", (
            f"Expected task.status='completed', got {task.status!r}. "
            f"error_message={task.error_message!r}"
        )

        results_resp = client.get(RESULTS_URL.format(task_id))
        assert results_resp.status_code == 200, (
            f"Results endpoint failed: {results_resp.status_code} {results_resp.data}"
        )

        data = results_resp.data
        assert data["status"] == "completed"
        results = data.get("results") or {}

        # paragraph_results must exist and have entries
        paragraph_results = results.get("paragraph_results") or []
        assert isinstance(paragraph_results, list), "paragraph_results must be a list"
        assert len(paragraph_results) > 0, "paragraph_results must not be empty"

        # review_analysis_results must be present
        review_analysis = results.get("review_analysis_results")
        assert review_analysis is not None, (
            "review_analysis_results missing from payload"
        )
        assert "overall" in review_analysis, (
            "'overall' key missing from review_analysis_results"
        )


@patch(
    "core.services.capabilities.review_analysis_service.analyze_review_text",
    return_value=FAKE_REVIEW_ANALYSIS,
)
@patch(
    "core.views.views_dectection.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda f: f())
def test_review_task_fails_when_review_file_missing_from_disk(mock_on_commit, mock_starter, mock_analyze, tmp_path):
    """
    When review_file.stored_path does not exist on disk,
    run_review_detection_task calls _mark_review_task_failed → status='failed'.
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")

        paper_stored = _write_file(tmp_media, "review/paper2.txt", _PAPER_TEXT)
        paper_file = make_file_management(
            user=user, resource_type="review_paper",
            stored_path=paper_stored, file_name="paper2.txt",
        )
        # review_file stored_path does NOT exist
        review_file = make_file_management(
            user=user, resource_type="review_file",
            stored_path="review/missing_review.txt",
            file_name="missing_review.txt",
            linked_file=paper_file,
        )

        client = APIClient()
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [paper_file.id, review_file.id],
            "task_name": "Missing review file test",
        }, format="json")

        assert resp.status_code in (200, 201), f"Create failed: {resp.data}"
        task_id = resp.data["task_id"]

        task = DetectionTask.objects.get(id=task_id)
        assert task.status == "failed", (
            f"Expected task.status='failed' when review file missing, got {task.status!r}"
        )
        assert task.error_message, "error_message should not be empty"
