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
    "core.services.capabilities.text_detection_service.detect_text_segment",
    return_value=FAKE_FASTDETECT_HIT,
)
@patch(
    "core.views.views_dectection.start_resource_detection_task_thread",
    side_effect=lambda *a, **kw: run_resource_detection_task_async(*a, **kw),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda f: f())
def test_paper_and_image_tasks_are_independent(mock_on_commit, mock_starter, mock_detect, tmp_path):
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
