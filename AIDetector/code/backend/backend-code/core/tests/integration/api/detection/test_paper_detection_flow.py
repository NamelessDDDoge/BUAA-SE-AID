"""
Task 1: Paper task creation validation.

Covers:
- wrong resource_type → 400
- foreign file (other user's file) → 400/404
- missing file_ids → 400
- task_name auto-generated when omitted
- reviewer role blocked by permission check → 403
"""
import pytest
import tempfile, os
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


@pytest.fixture
def media_root(tmp_path):
    return str(tmp_path)


# -------------------------------------------------------------------
# T1-A: wrong resource_type (image file submitted as paper task) → 400
# -------------------------------------------------------------------
def test_paper_task_rejects_image_resource_type(client, media_root):
    with override_settings(MEDIA_ROOT=media_root):
        user = make_user(role="publisher")
        image_file = make_file_management(user=user, resource_type="image")
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [image_file.id],
        }, format="json")

        assert resp.status_code == 400, (
            f"Expected 400 for image file submitted as paper task, got {resp.status_code}: {resp.data}"
        )
        # Error message must mention something about file type
        msg = str(resp.data.get("message", "")).lower()
        assert "paper" in msg or "resource" in msg or "file" in msg, (
            f"Error message does not mention file type issue: {resp.data}"
        )
        # No task should have been created
        assert not DetectionTask.objects.filter(user=user).exists()


# -------------------------------------------------------------------
# T1-B: mixed types (paper + image) → 400
# -------------------------------------------------------------------
def test_paper_task_rejects_mixed_resource_types(client, media_root):
    with override_settings(MEDIA_ROOT=media_root):
        user = make_user(role="publisher")
        paper_file = make_file_management(user=user, resource_type="paper")
        image_file = make_file_management(user=user, resource_type="image")
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [paper_file.id, image_file.id],
        }, format="json")

        assert resp.status_code == 400, (
            f"Expected 400 for mixed resource types, got {resp.status_code}: {resp.data}"
        )
        assert not DetectionTask.objects.filter(user=user).exists()


# -------------------------------------------------------------------
# T1-C: foreign file (belongs to another user) → 400/404
# -------------------------------------------------------------------
def test_paper_task_rejects_foreign_file(client, media_root):
    with override_settings(MEDIA_ROOT=media_root):
        user = make_user(role="publisher")
        other = make_user(role="publisher")
        foreign_file = make_file_management(user=other, resource_type="paper")
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [foreign_file.id],
        }, format="json")

        # The orchestrator raises FileNotFoundError → view returns 404
        assert resp.status_code in (400, 404), (
            f"Expected 400 or 404 for foreign file, got {resp.status_code}: {resp.data}"
        )
        assert not DetectionTask.objects.filter(user=user).exists()


# -------------------------------------------------------------------
# T1-D: empty file_ids list → 400
# -------------------------------------------------------------------
def test_paper_task_rejects_empty_file_ids(client, media_root):
    with override_settings(MEDIA_ROOT=media_root):
        user = make_user(role="publisher")
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [],
        }, format="json")

        assert resp.status_code == 400, (
            f"Expected 400 for empty file_ids, got {resp.status_code}: {resp.data}"
        )


# -------------------------------------------------------------------
# T1-E: task_name auto-generated when omitted
# -------------------------------------------------------------------
def test_paper_task_auto_generates_task_name_when_omitted(client, media_root):
    with override_settings(MEDIA_ROOT=media_root):
        user = make_user(role="publisher")
        paper_file = make_file_management(user=user, resource_type="paper",
                                          stored_path="papers/test.pdf")
        # Patch out the async runner to avoid disk/network calls
        with patch(
            "core.views.views_dectection.start_resource_detection_task_thread"
        ):
            client.force_authenticate(user)
            resp = client.post(CREATE_URL, {
                "task_type": "paper",
                "file_ids": [paper_file.id],
                # No task_name provided
            }, format="json")

        assert resp.status_code in (200, 201), (
            f"Expected 200/201, got {resp.status_code}: {resp.data}"
        )
        task = DetectionTask.objects.get(id=resp.data["task_id"])
        assert task.task_name, "task_name should be auto-generated, but is empty"
        assert "论文检测" in task.task_name, (
            f"Auto-generated task_name does not contain '论文检测': {task.task_name!r}"
        )


# -------------------------------------------------------------------
# T1-F: reviewer role does not have 'submit' permission → 403
# -------------------------------------------------------------------
def test_paper_task_blocked_for_reviewer_role(client, media_root):
    with override_settings(MEDIA_ROOT=media_root):
        reviewer = make_user(role="reviewer")
        paper_file = make_file_management(user=reviewer, resource_type="paper")
        client.force_authenticate(reviewer)

        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [paper_file.id],
            "task_name": "reviewer attempt",
        }, format="json")

        assert resp.status_code == 403, (
            f"Expected 403 for reviewer without submit permission, got {resp.status_code}: {resp.data}"
        )
        assert not DetectionTask.objects.filter(user=reviewer).exists()


# -------------------------------------------------------------------
# T1-G: unauthenticated request → 401
# -------------------------------------------------------------------
def test_paper_task_requires_authentication(client, media_root):
    with override_settings(MEDIA_ROOT=media_root):
        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [1],
        }, format="json")

        assert resp.status_code == 401, (
            f"Expected 401 for unauthenticated request, got {resp.status_code}"
        )


"""
Task 2: Paper detection complete chain — fast tier.
"""
import os
import pytest
import tempfile
from unittest.mock import patch
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import DetectionTask
from core.services.orchestrators.resource_task_orchestrator import run_resource_detection_task_async
from core.tests.factories import make_user, make_file_management

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

CREATE_URL = "/api/resource-task/create/"
RESULTS_URL = "/api/paper-results/{}/"

FAKE_FASTDETECT_HIT = {
    "data": {
        "prob": 0.92,
        "details": {"label": "AI", "confidence": 0.92},
    }
}

# Minimal document text to satisfy preprocess_document
_PAPER_TEXT = (
    "Abstract\n\nThis study examines machine-generated text.\n\n"
    "Introduction\n\nAI writing tools have proliferated rapidly.\n\n"
    "Conclusion\n\nFurther research is needed.\n"
)


def _make_paper_on_disk(media_root: str, stored_path: str = "papers/sample.txt") -> str:
    full = os.path.join(media_root, stored_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(_PAPER_TEXT)
    return stored_path


@pytest.fixture
def tmp_media(tmp_path):
    return str(tmp_path)


@patch(
    "core.services.capabilities.text_detection_service.detect_text_segment",
    return_value=FAKE_FASTDETECT_HIT,
)
@patch(
    "core.views.views_dectection.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda f: f())
def test_paper_detection_complete_chain(mock_on_commit, mock_starter, mock_detect, tmp_media):
    """
    Full happy-path: create → sync execution → poll → results.

    Assertions:
    - POST returns 200/201 with task_id
    - DetectionTask in DB transitions to 'completed'
    - GET /api/paper-results/<task_id>/ returns status='completed'
    - Result payload contains 'paragraph_results' list
    - At least one paragraph_result has probability >= 0.5 (our mock returns 0.92)
    """
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")
        stored_path = _make_paper_on_disk(tmp_media, "papers/sample.txt")
        paper_file = make_file_management(
            user=user,
            resource_type="paper",
            stored_path=stored_path,
            file_name="sample.txt",
        )

        client = APIClient()
        client.force_authenticate(user)

        create_resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [paper_file.id],
            "task_name": "Fast-tier paper test",
        }, format="json")

        assert create_resp.status_code in (200, 201), (
            f"Create failed: {create_resp.status_code} {create_resp.data}"
        )
        task_id = create_resp.data["task_id"]
        assert task_id is not None

        # Sync execution should have completed before on_commit fires;
        # re-read from DB
        task = DetectionTask.objects.get(id=task_id)
        assert task.status == "completed", (
            f"Expected task status='completed' after sync run, got {task.status!r}. "
            f"error_message={task.error_message!r}"
        )

        # Poll results via REST
        results_resp = client.get(RESULTS_URL.format(task_id))
        assert results_resp.status_code == 200, (
            f"Results endpoint failed: {results_resp.status_code} {results_resp.data}"
        )

        data = results_resp.data
        assert data["status"] == "completed"
        assert data["task_id"] == task_id

        # Shape: paragraph_results must be a list
        results = data.get("results") or {}
        paragraph_results = results.get("paragraph_results") or []
        assert isinstance(paragraph_results, list), (
            f"paragraph_results should be a list, got: {type(paragraph_results)}"
        )
        assert len(paragraph_results) > 0, (
            "paragraph_results is empty — detection produced no output"
        )

        # At least one paragraph flagged by mock (prob=0.92 > threshold 0.5)
        high_prob = [p for p in paragraph_results if p.get("probability", 0) >= 0.5]
        assert len(high_prob) > 0, (
            f"No paragraph with probability >= 0.5 despite mock returning 0.92. "
            f"paragraph_results={paragraph_results}"
        )


@patch(
    "core.services.capabilities.text_detection_service.detect_text_segment",
    return_value=FAKE_FASTDETECT_HIT,
)
@patch(
    "core.views.views_dectection.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda f: f())
def test_paper_results_endpoint_requires_ownership(mock_on_commit, mock_starter, mock_detect, tmp_media):
    """
    GET /api/paper-results/<task_id>/ must return 404 for a task belonging to another user.
    """
    with override_settings(MEDIA_ROOT=tmp_media):
        owner = make_user(role="publisher")
        stored_path = _make_paper_on_disk(tmp_media, "papers/owned.txt")
        paper_file = make_file_management(
            user=owner, resource_type="paper",
            stored_path=stored_path, file_name="owned.txt",
        )

        owner_client = APIClient()
        owner_client.force_authenticate(owner)
        create_resp = owner_client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [paper_file.id],
            "task_name": "owner task",
        }, format="json")
        task_id = create_resp.data["task_id"]

        attacker = make_user(role="publisher")
        attacker_client = APIClient()
        attacker_client.force_authenticate(attacker)

        resp = attacker_client.get(RESULTS_URL.format(task_id))
        assert resp.status_code == 404, (
            f"Expected 404 when accessing another user's task, got {resp.status_code}: {resp.data}"
        )


def test_paper_results_endpoint_returns_404_for_nonexistent_task():
    """
    GET /api/paper-results/999999/ returns 404 with a proper message (not a DRF default).
    """
    user = make_user(role="publisher")
    client = APIClient()
    client.force_authenticate(user)

    resp = client.get(RESULTS_URL.format(999999))
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    # The view returns {"message": "Detection task not found"}, not DRF's {"detail": "Not found."}
    assert "message" in resp.data, (
        f"Expected 'message' key in 404 response, got: {resp.data}"
    )


"""
Task 3: Paper detection failure handling.
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

_PAPER_TEXT = (
    "Abstract\n\nThis study examines machine-generated text.\n\n"
    "Body\n\nAI writing tools have proliferated rapidly.\n\n"
)


def _write_paper(tmp_media, rel="papers/err_test.txt"):
    full = os.path.join(tmp_media, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(_PAPER_TEXT)
    return rel


@patch(
    "core.services.capabilities.text_detection_service.detect_text_segment",
    side_effect=ConnectionError("FastDetect unreachable"),
)
@patch(
    "core.views.views_dectection.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda f: f())
def test_paper_detection_service_unavailable_task_still_completes(mock_on_commit, mock_starter, mock_detect, tmp_path):
    """
    When detect_text_segment raises, _detect_segment_probability catches it
    and returns probability=0.0 with an error detail. The task should still
    reach status='completed' (not 'failed'), and each paragraph result should
    have label='unavailable'.
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")
        stored = _write_paper(tmp_media)
        paper_file = make_file_management(
            user=user, resource_type="paper",
            stored_path=stored, file_name="err_test.txt",
        )

        client = APIClient()
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [paper_file.id],
            "task_name": "Service down test",
        }, format="json")

        assert resp.status_code in (200, 201), f"Create failed: {resp.data}"
        task_id = resp.data["task_id"]

        task = DetectionTask.objects.get(id=task_id)
        # text_detection_service catches the exception; task should complete
        assert task.status == "completed", (
            f"Task should complete even when detect_text_segment raises, got {task.status!r}. "
            f"error_message={task.error_message!r}"
        )

        # All paragraphs should have label='unavailable'
        text_results = task.text_detection_results or {}
        items = text_results.get("items") or [text_results]
        for item in items:
            para_results = item.get("paragraph_results") or []
            for para in para_results:
                assert para.get("label") == "unavailable", (
                    f"Expected label='unavailable' when service down, got: {para.get('label')!r}"
                )


@patch(
    "core.views.views_dectection.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda f: f())
def test_paper_detection_fails_when_stored_path_missing(mock_on_commit, mock_starter, tmp_path):
    """
    If stored_path points to a non-existent file, run_paper_detection_task
    calls _mark_task_failed → task.status should become 'failed'.
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")
        # stored_path does NOT exist on disk
        paper_file = make_file_management(
            user=user, resource_type="paper",
            stored_path="papers/does_not_exist.pdf",
            file_name="does_not_exist.pdf",
        )

        client = APIClient()
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [paper_file.id],
            "task_name": "Missing file test",
        }, format="json")

        assert resp.status_code in (200, 201), f"Create failed: {resp.data}"
        task_id = resp.data["task_id"]

        task = DetectionTask.objects.get(id=task_id)
        assert task.status == "failed", (
            f"Expected task.status='failed' when file is missing, got {task.status!r}"
        )
        assert task.error_message, "error_message should not be empty on failure"
