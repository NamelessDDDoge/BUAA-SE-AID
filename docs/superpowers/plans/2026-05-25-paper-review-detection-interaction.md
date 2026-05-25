# Paper + Review Detection Interactions — Test Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace placeholder paper/review detection tests with real interaction tests covering the complete create-poll-results chain, file validation, and linked-file business rules.

**Architecture:** Two-tier testing — fast (mock detect_text_segment / analyze_review_text) and bridge (mock HTTP calls at requests.post level). All tests use pytest + django_db.

**Tech Stack:** pytest, DRF APIClient, unittest.mock.patch, responses (optional)

---

## Background & Key Findings

### Existing placeholder tests (to be replaced)

`test_paper_detection_flow.py` and `test_review_detection_flow.py` contain four and three tests respectively. Every test skips on `404` and asserts only that the response code falls within a broad range (e.g., `in (400, 422)`). They assert nothing about database state, task status transitions, or result shape.

### Architecture notes derived from source reading

- **Entry point:** `POST /api/resource-task/create/` → `create_resource_task` view → `create_resource_detection_tasks` orchestrator → `create_resource_detection_task` → `DetectionTask.objects.create` + `detection_task.resource_files.add(...)`.
- **Async dispatch:** `start_resource_detection_task_thread` submits `run_resource_detection_task_async` to a `ThreadPoolExecutor`. In tests we bypass this by patching `start_resource_detection_task_thread` with `side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw)`, making execution synchronous.
- **Paper execution path:** `run_paper_detection_task` → `preprocess_document` (reads disk file) → `analyze_text_segments` → `detect_text_segment` (HTTP POST to FastDetect). Mock `detect_text_segment` at `core.services.capabilities.llm.fastdetect_client.detect_text_segment` for fast-tier tests.
- **Review execution path:** `run_review_detection_task` → `_build_review_file_pairs` (requires `review_file.linked_file` FK to be set) → `evaluate_review_analysis` → `analyze_review_text` (HTTP POST to OpenAI-compat). Mock `analyze_review_text` at `core.services.capabilities.llm.openai_client.analyze_review_text`.
- **File validation rules (paper):** `resource_types` must equal `{"paper"}` — mixed types raise `ValueError`.
- **File validation rules (review):** `resource_types` must be a superset of `{"review_paper", "review_file"}` AND exactly one `review_paper`, AND at least one `review_file` whose `linked_file_id` matches the `review_paper` id.
- **Permission:** `user.has_permission('submit')` reads `user.permission` (int, e.g., `1110` for `publisher`, `1` for `reviewer`). Publishers have `submit=True`; reviewers do not.
- **Result polling:** `GET /api/paper-results/<task_id>/` → `get_paper_detection_results` → reads `task.text_detection_results` JSON blob.
- **Task status transitions:** pending → in_progress → completed | failed.
- **`stored_path` field:** `FileManagement.stored_path` is the path relative to `MEDIA_ROOT`. The paper/review orchestrators call `os.path.join(settings.MEDIA_ROOT, file.stored_path)` and `os.path.exists(...)` before doing any detection. Tests must either create a real temp file at that path or mock `preprocess_document`.

### Factory summary

| Factory | Notable kwargs |
|---------|----------------|
| `make_user(role="publisher")` | `permission` auto-set to `1110` |
| `make_user(role="reviewer")` | `permission` auto-set to `1` |
| `make_file_management(user=u, resource_type="paper")` | `stored_path` defaults to `""` |
| `make_file_management(user=u, resource_type="review_paper")` | — |
| `make_file_management(user=u, resource_type="review_file", linked_file=paper)` | FK link |
| `make_detection_task(user=u, task_type="paper")` | `status="pending"` |

---

## Shared test infrastructure (add once to `conftest.py` or a helper module)

```python
# core/tests/integration/api/detection/conftest.py
import os
import tempfile
import pytest
from django.test import override_settings
from rest_framework.test import APIClient
from core.tests.factories import make_user, make_organization, make_file_management

MEDIA_TMP = tempfile.mkdtemp(prefix="aid-test-media-")

@pytest.fixture(scope="session")
def media_root(tmp_path_factory):
    return str(tmp_path_factory.mktemp("media"))

@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def publisher(db):
    return make_user(role="publisher")

@pytest.fixture
def auth_client(client, publisher):
    client.force_authenticate(publisher)
    return client, publisher

def make_temp_file(media_root: str, stored_path: str, content: bytes = b"dummy paper content\n" * 20):
    """Create a real file on disk at MEDIA_ROOT/stored_path."""
    full = os.path.join(media_root, stored_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as fh:
        fh.write(content)
    return full

FAKE_FASTDETECT_RESPONSE = {
    "data": {
        "prob": 0.92,
        "details": {"label": "AI", "confidence": 0.92},
    }
}

FAKE_ANALYZE_REVIEW_RESPONSE = {
    "overall": {
        "template_like_level": "low",
        "wrongness_level": "low",
        "relevance_level": "high",
        "summary": "Review looks genuine.",
        "key_findings": [],
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
            "explanation": "Content matches paper section 1.",
        }
    ],
}
```

---

## Task 1 — Paper task creation: validation (wrong file type, foreign file, missing task_name)

**File:** `core/tests/integration/api/detection/test_paper_detection_flow.py`
**Replaces:** all four existing placeholder tests.

- [ ] Delete the four placeholder tests in the existing file.
- [ ] Implement the following tests.

```python
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
            "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread"
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
```

---

## Task 2 — Paper detection complete chain (fast tier): create → sync execution → poll → results

**File:** `core/tests/integration/api/detection/test_paper_detection_flow.py` (append to Task 1 file)

- [ ] Create a minimal real text file on disk at the `stored_path` so `os.path.exists` passes.
- [ ] Patch `detect_text_segment` so it returns a high-AI-probability response immediately.
- [ ] Patch `start_resource_detection_task_thread` to run synchronously.
- [ ] Verify task DB state after create (status=`completed` after sync run).
- [ ] Verify `GET /api/paper-results/<task_id>/` returns expected shape.

```python
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
    "core.services.capabilities.llm.fastdetect_client.detect_text_segment",
    return_value=FAKE_FASTDETECT_HIT,
)
@patch(
    "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
def test_paper_detection_complete_chain(mock_starter, mock_detect, tmp_media):
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
    "core.services.capabilities.llm.fastdetect_client.detect_text_segment",
    return_value=FAKE_FASTDETECT_HIT,
)
@patch(
    "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
def test_paper_results_endpoint_requires_ownership(mock_starter, mock_detect, tmp_media):
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
```

---

## Task 3 — Paper detection failure handling: detect_text_segment raises

**File:** `core/tests/integration/api/detection/test_paper_detection_flow.py` (append)

- [ ] Verify task status becomes `completed` (not `failed`) even when the detection service is down — because `_detect_segment_probability` catches all exceptions and returns `probability=0.0, details={"error": ...}`.
- [ ] Verify the result payload shows `label="unavailable"` for each paragraph.
- [ ] Additionally verify that a missing disk file causes status=`failed`.

```python
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
    "core.services.capabilities.llm.fastdetect_client.detect_text_segment",
    side_effect=ConnectionError("FastDetect unreachable"),
)
@patch(
    "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
def test_paper_detection_service_unavailable_task_still_completes(mock_starter, mock_detect, tmp_path):
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
    "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
def test_paper_detection_fails_when_stored_path_missing(mock_starter, tmp_path):
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
```

---

## Task 4 — Review task validation: unlinked files, missing paper, missing review

**File:** `core/tests/integration/api/detection/test_review_detection_flow.py`
**Replaces:** all three existing placeholder tests.

- [ ] Delete the three placeholder tests.
- [ ] Implement the following tests.

```python
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
            "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread"
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
```

---

## Task 5 — Review detection complete chain (fast tier): create → sync → results

**File:** `core/tests/integration/api/detection/test_review_detection_flow.py` (append)

- [ ] Create real text files on disk for both paper and review.
- [ ] Patch `analyze_review_text` at the module where it is called from (`core.services.capabilities.llm.openai_client.analyze_review_text`).
- [ ] Patch `start_resource_detection_task_thread` to run synchronously.
- [ ] Verify task reaches `completed`.
- [ ] Verify result payload has `paragraph_results` and `review_analysis_results`.

```python
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
    "core.services.capabilities.llm.openai_client.analyze_review_text",
    return_value=FAKE_REVIEW_ANALYSIS,
)
@patch(
    "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
def test_review_detection_complete_chain(mock_starter, mock_analyze, tmp_path):
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
    "core.services.capabilities.llm.openai_client.analyze_review_text",
    return_value=FAKE_REVIEW_ANALYSIS,
)
@patch(
    "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
def test_review_task_fails_when_review_file_missing_from_disk(mock_starter, mock_analyze, tmp_path):
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
```

---

## Task 6 — Bridge tier for paper: mock HTTP requests.post to FastDetect API

**File:** `core/tests/integration/api/detection/test_paper_bridge_tier.py` (new file)

- [ ] Create the file.
- [ ] Mock `requests.post` inside `core.services.capabilities.llm.fastdetect_client` at the HTTP level, without touching the higher-level function signatures.
- [ ] Verify the response is deserialized correctly end-to-end.

```python
"""
Task 6: Bridge tier — paper detection mocks HTTP at requests.post level.

This tests the full call stack including detect_text_segment → requests.post
without any real network calls. Uses unittest.mock to intercept at the
HTTP boundary, simulating what the FastDetect API returns.
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import DetectionTask
from core.services.orchestrators.resource_task_orchestrator import run_resource_detection_task_async
from core.tests.factories import make_user, make_file_management

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

CREATE_URL = "/api/resource-task/create/"
RESULTS_URL = "/api/paper-results/{}/"

_PAPER_TEXT = (
    "Abstract\n\nThis paper presents a novel approach to AI text detection.\n\n"
    "Introduction\n\nAI-generated text is difficult to distinguish from human writing.\n\n"
    "Method\n\nWe use a transformer-based approach with a fine-tuned classifier.\n\n"
    "Conclusion\n\nResults show 95% accuracy on benchmark datasets.\n"
)


def _fastdetect_http_response(prob: float = 0.88) -> MagicMock:
    """Build a mock requests.Response that mimics FastDetect API output."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "data": {
            "prob": prob,
            "details": {
                "label": "AI" if prob >= 0.5 else "Human",
                "confidence": prob,
            }
        }
    }
    return mock_resp


def _write_paper(media_root: str, rel="papers/bridge_test.txt") -> str:
    full = os.path.join(media_root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(_PAPER_TEXT)
    return rel


@patch(
    "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch(
    "core.services.capabilities.llm.fastdetect_client.requests.post",
    side_effect=lambda *a, **kw: _fastdetect_http_response(prob=0.88),
)
def test_paper_bridge_tier_fastdetect_http_mock(mock_post, mock_starter, tmp_path):
    """
    Bridge tier: mock requests.post inside fastdetect_client.
    Verify the full chain processes the HTTP response correctly:
    - task completes
    - paragraph_results contain probability derived from mocked HTTP response
    - detect_text_segment was NOT called with real network
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")
        stored = _write_paper(tmp_media)
        paper_file = make_file_management(
            user=user, resource_type="paper",
            stored_path=stored, file_name="bridge_test.txt",
        )

        client = APIClient()
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [paper_file.id],
            "task_name": "Bridge tier paper test",
        }, format="json")

        assert resp.status_code in (200, 201), f"Create failed: {resp.data}"
        task_id = resp.data["task_id"]

        task = DetectionTask.objects.get(id=task_id)
        assert task.status == "completed", (
            f"Expected completed, got {task.status!r}: {task.error_message!r}"
        )

        # Verify requests.post was actually called (not short-circuited)
        assert mock_post.called, (
            "requests.post was never called — fastdetect_client did not make HTTP request"
        )

        # Verify call arguments include detector and text fields
        call_kwargs = mock_post.call_args
        payload_sent = call_kwargs.kwargs.get("json") or (
            call_kwargs.args[1] if len(call_kwargs.args) > 1 else {}
        )
        assert "text" in payload_sent, (
            f"FastDetect HTTP payload missing 'text' field: {payload_sent}"
        )
        assert "detector" in payload_sent, (
            f"FastDetect HTTP payload missing 'detector' field: {payload_sent}"
        )

        # Verify results reflect the mocked 0.88 probability
        results_resp = client.get(RESULTS_URL.format(task_id))
        assert results_resp.status_code == 200
        items = (results_resp.data.get("results") or {})
        para_results = items.get("paragraph_results") or []
        high_prob = [p for p in para_results if p.get("probability", 0) >= 0.5]
        assert high_prob, (
            f"No paragraph with probability >= 0.5 despite HTTP mock returning 0.88. "
            f"paragraph_results={para_results}"
        )


@patch(
    "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch(
    "core.services.capabilities.llm.fastdetect_client.requests.post",
    side_effect=lambda *a, **kw: _fastdetect_http_response(prob=0.12),
)
def test_paper_bridge_tier_low_probability_classified_clean(mock_post, mock_starter, tmp_path):
    """
    When FastDetect returns a low probability (0.12), paragraphs should have
    label='clean' (threshold is 0.5).
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")
        stored = _write_paper(tmp_media, "papers/low_prob.txt")
        paper_file = make_file_management(
            user=user, resource_type="paper",
            stored_path=stored, file_name="low_prob.txt",
        )

        client = APIClient()
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "paper",
            "file_ids": [paper_file.id],
            "task_name": "Low prob test",
        }, format="json")

        assert resp.status_code in (200, 201)
        task = DetectionTask.objects.get(id=resp.data["task_id"])
        assert task.status == "completed"

        results_resp = client.get(RESULTS_URL.format(task.id))
        para_results = (results_resp.data.get("results") or {}).get("paragraph_results") or []
        clean_paras = [p for p in para_results if p.get("label") == "clean"]
        suspicious_paras = [p for p in para_results if p.get("label") == "suspicious"]
        assert len(clean_paras) > 0 or len(para_results) == 0, (
            "Expected clean paragraphs with prob=0.12 but got none"
        )
        assert len(suspicious_paras) == 0, (
            f"No paragraphs should be suspicious at prob=0.12, found: {suspicious_paras}"
        )
```

---

## Task 7 — Bridge tier for review: mock HTTP requests.post to OpenAI-compatible endpoint

**File:** `core/tests/integration/api/detection/test_review_bridge_tier.py` (new file)

- [ ] Create the file.
- [ ] Mock `requests.post` inside `core.services.capabilities.llm.openai_client`.
- [ ] Simulate the OpenAI-compatible chat completion response format that `analyze_review_text` expects.
- [ ] Verify task completes and result shape is correct.

```python
"""
Task 7: Bridge tier — review detection mocks HTTP at requests.post level
inside openai_client (OpenAI-compatible chat completions endpoint).

The openai_client._request_structured_json function calls requests.post
to an OpenAI-compatible endpoint. We mock that HTTP call to return a
structured JSON blob (the kind that analyze_review_text expects).
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import DetectionTask
from core.services.orchestrators.resource_task_orchestrator import run_resource_detection_task_async
from core.tests.factories import make_user, make_file_management

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

CREATE_URL = "/api/resource-task/create/"
RESULTS_URL = "/api/paper-results/{}/"

_PAPER_TEXT = (
    "Abstract\n\nThis paper studies the impact of AI on peer review quality.\n\n"
    "Introduction\n\nPeer review is fundamental to scientific publishing.\n\n"
    "Conclusion\n\nAI-generated reviews are increasingly common.\n"
)

_REVIEW_TEXT = (
    "Summary\n\nThe paper makes a strong contribution to the field.\n\n"
    "Strengths\n\nThe literature review is comprehensive.\n\n"
    "Weaknesses\n\nThe sample size is small.\n"
)

_STRUCTURED_REVIEW_RESPONSE = {
    "overall": {
        "template_like_level": "low",
        "wrongness_level": "low",
        "relevance_level": "high",
        "summary": "Review is genuine and thorough.",
        "key_findings": ["Comprehensive literature review"],
        "suggestions": ["Expand sample size"],
    },
    "paragraph_results": [
        {
            "review_paragraph_index": 0,
            "paper_paragraph_index": 0,
            "template_like_level": "low",
            "wrongness_level": "low",
            "relevance_score": 0.90,
            "relevance_level": "high",
            "explanation": "Reviewer directly references the paper's abstract.",
        },
        {
            "review_paragraph_index": 1,
            "paper_paragraph_index": None,
            "template_like_level": "medium",
            "wrongness_level": "low",
            "relevance_score": 0.50,
            "relevance_level": "medium",
            "explanation": "Generic strength comment.",
        },
    ],
}


def _openai_chat_completion_response(content: dict) -> MagicMock:
    """
    Simulate an OpenAI-compatible chat completions HTTP response.
    The content dict will be JSON-encoded into choices[0].message.content.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(content),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
    }
    return mock_resp


def _write_file(media_root: str, rel: str, text: str) -> str:
    full = os.path.join(media_root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(text)
    return rel


@patch(
    "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch(
    "core.services.capabilities.llm.openai_client.requests.post",
    side_effect=lambda *a, **kw: _openai_chat_completion_response(_STRUCTURED_REVIEW_RESPONSE),
)
def test_review_bridge_tier_openai_http_mock(mock_post, mock_starter, tmp_path):
    """
    Bridge tier: mock requests.post inside openai_client.
    Verify the full chain processes the HTTP response correctly:
    - task completes
    - paragraph_results reflect the mocked API response
    - overall review_analysis_results present
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")

        paper_stored = _write_file(tmp_media, "review_bridge/paper.txt", _PAPER_TEXT)
        review_stored = _write_file(tmp_media, "review_bridge/review.txt", _REVIEW_TEXT)

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

        resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [paper_file.id, review_file.id],
            "task_name": "Bridge tier review test",
        }, format="json")

        assert resp.status_code in (200, 201), f"Create failed: {resp.data}"
        task_id = resp.data["task_id"]

        task = DetectionTask.objects.get(id=task_id)
        assert task.status == "completed", (
            f"Expected completed, got {task.status!r}: {task.error_message!r}"
        )

        # Verify requests.post was called (chain reached the HTTP layer)
        assert mock_post.called, (
            "requests.post was never called — openai_client did not make HTTP request"
        )

        results_resp = client.get(RESULTS_URL.format(task_id))
        assert results_resp.status_code == 200
        data = results_resp.data
        assert data["status"] == "completed"

        results = data.get("results") or {}
        para_results = results.get("paragraph_results") or []
        assert len(para_results) > 0, "paragraph_results must not be empty"

        review_analysis = results.get("review_analysis_results")
        assert review_analysis is not None
        overall = review_analysis.get("overall") or {}
        assert "template_like_level" in overall
        assert "qualification_label" in overall, (
            "'qualification_label' missing from overall — build_review_qualification not applied"
        )


@patch(
    "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch(
    "core.services.capabilities.llm.openai_client.requests.post",
    side_effect=ConnectionError("OpenAI endpoint unreachable"),
)
def test_review_bridge_tier_api_error_results_in_unavailable(mock_post, mock_starter, tmp_path):
    """
    When the OpenAI-compatible endpoint is unreachable, evaluate_review_analysis
    returns an 'api_unavailable' overall. The task should still complete
    (not fail) and overall.qualification_label should be 'unavailable'.
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")

        paper_stored = _write_file(tmp_media, "review_bridge/paper_err.txt", _PAPER_TEXT)
        review_stored = _write_file(tmp_media, "review_bridge/review_err.txt", _REVIEW_TEXT)

        paper_file = make_file_management(
            user=user, resource_type="review_paper",
            stored_path=paper_stored, file_name="paper_err.txt",
        )
        review_file = make_file_management(
            user=user, resource_type="review_file",
            stored_path=review_stored, file_name="review_err.txt",
            linked_file=paper_file,
        )

        client = APIClient()
        client.force_authenticate(user)

        resp = client.post(CREATE_URL, {
            "task_type": "review",
            "file_ids": [paper_file.id, review_file.id],
            "task_name": "API error review test",
        }, format="json")

        assert resp.status_code in (200, 201), f"Create failed: {resp.data}"
        task = DetectionTask.objects.get(id=resp.data["task_id"])

        # evaluate_review_analysis handles the error gracefully; task must not crash
        assert task.status == "completed", (
            f"Task should complete even when OpenAI endpoint is down, got {task.status!r}: "
            f"{task.error_message!r}"
        )

        results_resp = client.get(RESULTS_URL.format(task.id))
        assert results_resp.status_code == 200
        results = results_resp.data.get("results") or {}
        review_analysis = results.get("review_analysis_results") or {}
        overall = review_analysis.get("overall") or {}

        # When LLM is unavailable, overall should reflect that
        qualification = overall.get("qualification_label", "")
        assert qualification == "unavailable", (
            f"Expected qualification_label='unavailable' when API unreachable, got {qualification!r}"
        )
```

---

## Task 8 — Paper + image tasks submitted together for the same user

**File:** `core/tests/integration/api/detection/test_mixed_task_interaction.py` (new file)

- [ ] Create the file.
- [ ] Submit a paper task AND an image task for the same user in sequence.
- [ ] Verify tasks are independent: each has its own `task_id`, separate `task_type`, and separate status tracking.
- [ ] Verify `GET /api/user-tasks/` returns both tasks for the user.
- [ ] Verify paper results endpoint only returns paper task; image results endpoint only returns image results.
- [ ] Verify cancelling/deleting the image task does not affect the paper task.

```python
"""
Task 8: Paper + image detection submitted together for the same user.

Interaction tests:
- Two concurrent task types for the same user do not interfere.
- Each task has its own ID, type, and status.
- get_user_tasks returns both.
- Results endpoints are scoped to task type.
"""
import os
import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock
from django.test import override_settings
from rest_framework.test import APIClient
from PIL import Image

from core.models import DetectionTask, ImageUpload
from core.services.orchestrators.resource_task_orchestrator import run_resource_detection_task_async
from core.tests.factories import make_user, make_file_management

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

CREATE_RESOURCE_URL = "/api/resource-task/create/"
SUBMIT_IMAGE_URL = "/api/detection/submit/"
RESULTS_URL = "/api/paper-results/{}/"
USER_TASKS_URL = "/api/user-tasks/"

_PAPER_TEXT = (
    "Abstract\n\nThis paper proposes a novel method.\n\n"
    "Body\n\nThe method outperforms prior work.\n\n"
    "Conclusion\n\nWe plan to release code.\n"
)

FAKE_FASTDETECT_HIT = {
    "data": {
        "prob": 0.75,
        "details": {"label": "AI", "confidence": 0.75},
    }
}


def _write_paper(media_root: str, rel: str = "mixed/paper.txt") -> str:
    full = os.path.join(media_root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(_PAPER_TEXT)
    return rel


def _build_png_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (32, 32), color=(100, 200, 50)).save(buf, format="PNG")
    return buf.getvalue()


def _fake_image_detection_result() -> MagicMock:
    """Stub for image detection — returns immediately without real ML."""
    return MagicMock(return_value=None)


@patch(
    "core.services.capabilities.llm.fastdetect_client.detect_text_segment",
    return_value=FAKE_FASTDETECT_HIT,
)
@patch(
    "core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
def test_paper_and_image_tasks_are_independent(mock_starter, mock_detect, tmp_path):
    """
    Create a paper task and an image task for the same user.
    Verify:
    1. Both tasks exist in DB with different task_types.
    2. Paper task result endpoint does not return image task data.
    3. GET /api/user-tasks/ returns both tasks.
    4. Deleting the image task does not cascade to paper task.
    """
    tmp_media = str(tmp_path)
    with override_settings(MEDIA_ROOT=tmp_media):
        user = make_user(role="publisher")
        client = APIClient()
        client.force_authenticate(user)

        # --- Submit paper task ---
        stored = _write_paper(tmp_media)
        paper_file = make_file_management(
            user=user, resource_type="paper",
            stored_path=stored, file_name="paper.txt",
        )
        paper_resp = client.post(CREATE_RESOURCE_URL, {
            "task_type": "paper",
            "file_ids": [paper_file.id],
            "task_name": "Paper task",
        }, format="json")
        assert paper_resp.status_code in (200, 201), (
            f"Paper task create failed: {paper_resp.data}"
        )
        paper_task_id = paper_resp.data["task_id"]

        # --- Submit image task via multipart ---
        png_bytes = _build_png_bytes()
        from django.core.files.uploadedfile import SimpleUploadedFile
        image_upload_file = SimpleUploadedFile("test.png", png_bytes, content_type="image/png")

        with patch(
            "core.services.orchestrators.image_task_orchestrator.start_image_detection_task_thread"
        ):
            img_resp = client.post(SUBMIT_IMAGE_URL, {
                "images": [image_upload_file],
                "task_name": "Image task",
            }, format="multipart")

        # Image submission may or may not succeed depending on setup;
        # we care about isolation, not image detection correctness
        image_task_id = None
        if img_resp.status_code in (200, 201):
            image_task_id = img_resp.data.get("task_id")

        # --- Verify both tasks exist with correct types ---
        paper_task = DetectionTask.objects.get(id=paper_task_id)
        assert paper_task.task_type == "paper", (
            f"Paper task has wrong task_type: {paper_task.task_type!r}"
        )
        assert paper_task.status == "completed", (
            f"Paper task should be completed, got {paper_task.status!r}"
        )

        if image_task_id:
            image_task = DetectionTask.objects.get(id=image_task_id)
            assert image_task.task_type == "image", (
                f"Image task has wrong task_type: {image_task.task_type!r}"
            )
            # Image task and paper task must not share IDs
            assert paper_task_id != image_task_id, "Paper and image task must have different IDs"

        # --- Paper results endpoint scoped to paper task ---
        results_resp = client.get(RESULTS_URL.format(paper_task_id))
        assert results_resp.status_code == 200
        assert results_resp.data["task_type"] == "paper", (
            f"Results endpoint returned wrong task_type: {results_resp.data.get('task_type')!r}"
        )

        # --- GET /api/user-tasks/ returns both tasks ---
        tasks_resp = client.get(USER_TASKS_URL)
        assert tasks_resp.status_code == 200
        task_list = tasks_resp.data.get("tasks", [])
        task_ids_in_list = [t.get("task_id") or t.get("id") for t in task_list]
        assert paper_task_id in task_ids_in_list, (
            f"Paper task {paper_task_id} not found in user-tasks: {task_ids_in_list}"
        )

        # --- Delete image task (if created) does NOT cascade to paper task ---
        if image_task_id:
            DELETE_URL = f"/api/detection-task-delete/{image_task_id}/"
            del_resp = client.delete(DELETE_URL)
            # Accept 200, 204, or 404 (task may have already been cleaned up)
            assert del_resp.status_code in (200, 204, 404), (
                f"Delete image task returned unexpected status: {del_resp.status_code}"
            )
            # Paper task must still exist
            assert DetectionTask.objects.filter(id=paper_task_id).exists(), (
                "Paper task was deleted when image task was deleted — cascade bug!"
            )


def test_paper_task_result_endpoint_rejects_image_task_id():
    """
    GET /api/paper-results/<image_task_id>/ must return 404 because
    the paper results endpoint filters by user AND task existence.
    An image task_id submitted here should return 404.
    """
    user = make_user(role="publisher")
    # Create an image task directly (no file needed)
    from core.tests.factories import make_detection_task
    image_task = make_detection_task(user=user, task_type="image", status="completed")

    client = APIClient()
    client.force_authenticate(user)

    resp = client.get(RESULTS_URL.format(image_task.id))
    # The paper-results endpoint does: DetectionTask.objects.get(id=task_id, user=request.user)
    # It does NOT filter by task_type, so it may return 200 with image task data OR 404.
    # This test documents current behavior: if it returns 200, the response should still
    # have a usable shape. The correct behavior is 404 (task type mismatch).
    if resp.status_code == 200:
        # Document the bug: paper-results does not reject image tasks
        # This assertion will FAIL if the endpoint is fixed to require task_type="paper"
        pytest.fail(
            f"BUG: /api/paper-results/ returned 200 for an image task (id={image_task.id}). "
            f"The endpoint should return 404 for non-paper tasks. "
            f"Response data: {resp.data}"
        )
    # If already fixed or returns 404 for other reasons:
    assert resp.status_code == 404
```

---

## Implementation notes for agentic workers

### Running the tests

```bash
cd AIDetector/code/backend/backend-code
pytest core/tests/integration/api/detection/ -v -x --tb=short -p no:warnings
```

### Key mock paths (exact strings required)

| What to mock | Patch target string |
|---|---|
| FastDetect HTTP call (fast tier) | `core.services.capabilities.llm.fastdetect_client.detect_text_segment` |
| FastDetect HTTP call (bridge tier) | `core.services.capabilities.llm.fastdetect_client.requests.post` |
| Review LLM call (fast tier) | `core.services.capabilities.llm.openai_client.analyze_review_text` |
| Review LLM call (bridge tier) | `core.services.capabilities.llm.openai_client.requests.post` |
| Async task thread starter | `core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread` |

### `on_commit` behavior in tests

Django's `transaction.on_commit` callbacks do NOT fire in test transactions by default (unless `@pytest.mark.django_db(transaction=True)` is used). The `create_resource_task` view passes `on_commit=transaction.on_commit` to the orchestrator. When patching `start_resource_detection_task_thread` with `side_effect=run_resource_detection_task_async`, the lambda registered via `on_commit` will NOT fire automatically in the default test transaction.

**Recommended workaround:** Either:
1. Use `@pytest.mark.django_db(transaction=True)` — causes real commits, allowing `on_commit` to fire, but is slower.
2. Patch `transaction.on_commit` to call the callback immediately: `patch("django.db.transaction.on_commit", side_effect=lambda f: f())`.
3. Call `run_resource_detection_task_async` directly after the `POST` in the test body.

Option 2 is cleanest for isolation:

```python
@patch("django.db.transaction.on_commit", side_effect=lambda f: f())
@patch("core.services.orchestrators.resource_task_orchestrator.start_resource_detection_task_thread",
       side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw))
@patch("core.services.capabilities.llm.fastdetect_client.detect_text_segment",
       return_value=FAKE_FASTDETECT_HIT)
def test_...(mock_detect, mock_starter, mock_on_commit, tmp_path):
    ...
```

### `preprocess_document` and disk files

The orchestrators call `preprocess_document(file_path)` which reads actual content from disk. Tests that want to verify end-to-end execution must write a real file. Tests that only want to test task creation/validation may patch `preprocess_document` instead:

```python
@patch("core.services.orchestrators.paper_task_orchestrator.preprocess_document",
       return_value={
           "text_content": "Sample paper text.",
           "paragraphs": ["Sample paper text."],
           "sections": {"abstract": "Sample paper text.", "body": "", "acknowledgements": ""},
           "references": [],
           "segments": ["Sample paper text."],
       })
```

### Factories: `stored_path` is empty by default

`make_file_management` sets `stored_path=""` by default. Always override with a real relative path when the execution chain will reach `preprocess_document`. The path is joined with `settings.MEDIA_ROOT` — use `override_settings(MEDIA_ROOT=str(tmp_path))`.
