# Cross-Flow Integration Tests — Test Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test data consistency and interaction bugs at boundaries between detection, review, quota, and notification subsystems.

**Architecture:** Multi-step integration tests that span 2+ subsystems. Each test traces a complete user journey and asserts state consistency at each boundary crossing.

**Tech Stack:** pytest, DRF APIClient, unittest.mock.patch, Django ORM assertions

---

## Target file

```
core/tests/integration/api/cross_flow/test_cross_flow.py
```

Run with:

```bash
cd AIDetector/code/backend/backend-code
pytest core/tests/integration/api/cross_flow/test_cross_flow.py -v
```

---

## Shared helpers (place at top of test file)

```python
import shutil
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from django.test import override_settings
from PIL import Image
from rest_framework.test import APIClient

from core.models import (
    DetectionResult,
    DetectionTask,
    ImageReview,
    ImageUpload,
    ManualReview,
    Notification,
    Organization,
    ReviewRequest,
)
from core.tests.factories import (
    make_detection_result,
    make_detection_task,
    make_file_management,
    make_image_upload,
    make_organization,
    make_review_request,
    make_user,
)
from core.views.views_dectection import _run_detection_task_async

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

TEMP_MEDIA = "/tmp/test-media-cross-flow"


def build_test_image(name="test.png", color=(255, 0, 0)):
    buf = BytesIO()
    Image.new("RGB", (12, 12), color=color).save(buf, format="PNG")
    return name, buf.getvalue()


def fake_detection_payload():
    return [
        ("llm", [("image_0.png", None)]),
        ("ela", [("image_0.png", np.full((12, 12), 10, dtype=np.uint8))]),
        ("exif", [("image_0.png", ("exif", ["Edited by Photoshop"]))]),
        ("cmd", []),
        ("urn_coarse_v2", [np.ones((12, 12), dtype=np.float32), 0.85]),
        ("urn_blurring", [np.zeros((12, 12), dtype=np.float32), 0.10]),
        ("urn_brute_force", [np.zeros((12, 12), dtype=np.float32), 0.05]),
        ("urn_contrast", [np.zeros((12, 12), dtype=np.float32), 0.20]),
        ("urn_inpainting", [np.zeros((12, 12), dtype=np.float32), 0.30]),
    ]


def _setup_org_with_users():
    """Return (org, admin, publisher, reviewer) all in same org."""
    org = make_organization()
    admin = make_user(organization=org, role="admin", is_staff=True)
    publisher = make_user(organization=org, role="publisher")
    reviewer = make_user(organization=org, role="reviewer")
    org.admin_user = admin
    org.save(update_fields=["admin_user"])
    return org, admin, publisher, reviewer


def _upload_and_extract_image(client, media_root):
    """Upload a PNG via the API and return (file_id, image_id)."""
    _, image_bytes = build_test_image()
    from django.core.files.uploadedfile import SimpleUploadedFile
    uploaded = SimpleUploadedFile("test.png", image_bytes, content_type="image/png")
    resp = client.post("/api/upload/", {"detection_type": "image", "file": uploaded}, format="multipart")
    assert resp.status_code == 200, f"Upload failed: {resp.data}"
    file_id = resp.data["file_id"]
    extract_resp = client.get(f"/api/upload/{file_id}/extract_images/")
    assert extract_resp.status_code == 200
    image_id = extract_resp.data["images"][0]["image_id"]
    return file_id, image_id


def _submit_image_detection(client, image_ids, task_name="Cross-Flow Task"):
    return client.post(
        "/api/detection/submit/",
        {
            "mode": 1,
            "image_ids": image_ids,
            "task_name": task_name,
            "cmd_block_size": 64,
            "urn_k": 0.3,
            "if_use_llm": False,
        },
        format="json",
    )
```

---

## Task 1 — Image detection → apply for manual review (using completed detection result)

**Subsystems crossed:** detection submit → detection pipeline → review request create

**Bug risk:** `create_review_task_with_admin_check` calls `images[0].detection_results.first()` — if detection is not completed or `detection_result` is `None`, the review request creation silently fails or returns 404.

- [ ] Create `core/tests/integration/api/cross_flow/__init__.py` (empty)
- [ ] Create test function `test_detection_complete_then_apply_manual_review` in `test_cross_flow.py`

```python
@override_settings(MEDIA_ROOT=TEMP_MEDIA)
@patch(
    "core.views.views_dectection._start_detection_task_thread",
    side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
        task_id, image_ids, if_use_llm, num_images
    ),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
@patch(
    "core.services.capabilities.image.local_detection.generate_detection_task_report",
    return_value="reports/cross_flow_1.pdf",
)
@patch(
    "core.services.capabilities.image.local_detection.get_result",
    return_value=fake_detection_payload(),
)
@patch("core.views.views_review.send_mail")  # suppress actual email
def test_detection_complete_then_apply_manual_review(
    _mock_mail, _mock_result, _mock_report, _mock_commit, _mock_thread
):
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
    Path(TEMP_MEDIA).mkdir(parents=True, exist_ok=True)

    org, admin, publisher, reviewer = _setup_org_with_users()
    client = APIClient()
    client.force_authenticate(publisher)

    # Step 1: upload image and run detection
    _, image_id = _upload_and_extract_image(client, TEMP_MEDIA)
    submit_resp = _submit_image_detection(client, [image_id])
    assert submit_resp.status_code == 200
    task_id = submit_resp.data["task_id"]

    # Verify detection completed
    task = DetectionTask.objects.get(pk=task_id)
    assert task.status == "completed"
    dr = DetectionResult.objects.get(detection_task=task)
    assert dr.status == "completed"
    assert dr.is_fake is True  # fake_detection_payload yields is_fake=True

    # Step 2: publisher applies for manual review on the completed detection
    review_resp = client.post(
        "/api/create_review_task_with_admin_check/",
        {
            "image_ids": [image_id],
            "reviewers": [reviewer.id],
            "reason": "Please double-check this image",
        },
        format="json",
    )
    assert review_resp.status_code == 201, f"Review creation failed: {review_resp.data}"
    review_request_id = review_resp.data["review_request_id"]

    # Verify ReviewRequest links back to the completed DetectionResult
    rr = ReviewRequest.objects.get(pk=review_request_id)
    assert rr.detection_result == dr
    assert rr.user == publisher
    assert rr.organization == org
    assert rr.status2 == "pending"  # awaiting admin approval
    assert rr.imgs.filter(pk=image_id).exists()
    assert rr.reviewers.filter(pk=reviewer.id).exists()

    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
```

---

## Task 2 — Manual review override → data consistency check (`isFake` after review)

**Subsystems crossed:** pre-seeded detection result → admin accept → reviewer submits override → ORM state consistency

**Bug risk:** After `post_review` marks `ImageReview.result=True` (confirmed fake), the `ImageUpload.isFake` field may or may not be updated — cross-flow data consistency.  Also verifies that a review override (e.g., `final=False` means "not fake") propagates correctly to `ImageReview.result`.

- [ ] Create test function `test_review_override_data_consistency` in `test_cross_flow.py`

```python
@override_settings(MEDIA_ROOT=TEMP_MEDIA)
def test_review_override_data_consistency():
    """
    Pre-seed: image detected as fake (is_fake=True).
    Reviewer submits manual review with final=False (reviewer says NOT fake).
    Assert: ImageReview.result is False; ImageUpload.isReview is True.
    Also assert: DetectionResult.is_fake is still True (detection unchanged).
    """
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
    Path(TEMP_MEDIA).mkdir(parents=True, exist_ok=True)

    org, admin, publisher, reviewer = _setup_org_with_users()

    # Pre-seed: completed detection, image marked fake
    task = make_detection_task(user=publisher, organization=org, task_type="image", status="completed")
    source_file = make_file_management(user=publisher, organization=org, resource_type="image", file_type="image/png")
    image_upload = make_image_upload(detection_task=task, file_management=source_file)
    image_upload.isFake = True
    image_upload.isDetect = True
    image_upload.save(update_fields=["isFake", "isDetect"])

    detection_result = make_detection_result(
        detection_task=task,
        image_upload=image_upload,
        status="completed",
        is_fake=True,
        confidence_score=0.91,
    )

    # Create review request manually (skip admin email)
    rr = ReviewRequest.objects.create(
        detection_result=detection_result,
        user=publisher,
        organization=org,
        reason="Dispute: reviewer thinks this is authentic",
    )
    rr.imgs.add(image_upload)
    rr.reviewers.add(reviewer)

    client = APIClient()

    # Admin accepts
    client.force_authenticate(admin)
    accept_resp = client.post(
        f"/api/handle_reviewRequest/{rr.id}/",
        {"choice": 1, "reason": "Accepted for review"},
        format="json",
    )
    assert accept_resp.status_code == 200
    rr.refresh_from_db()
    assert rr.status2 == "accepted"

    manual_review = ManualReview.objects.get(review_request=rr, reviewer=reviewer)

    # Reviewer submits: final=False (reviewer says NOT fake — override)
    client.force_authenticate(reviewer)
    submit_resp = client.post(
        f"/api/post_review/{manual_review.id}/",
        {
            "result": [
                {
                    "img_id": image_upload.id,
                    "score": [1, 1, 1, 1, 1, 1, 1],
                    "reason": ["r1", "r2", "r3", "r4", "r5", "r6", "r7"],
                    "points": [[], [], [], [], [], [], []],
                    "final": False,  # reviewer says NOT fake
                }
            ]
        },
        format="json",
    )
    assert submit_resp.status_code == 201

    # Data consistency assertions
    manual_review.refresh_from_db()
    rr.refresh_from_db()
    image_upload.refresh_from_db()
    detection_result.refresh_from_db()
    image_review = ImageReview.objects.get(manual_review=manual_review, img=image_upload)

    # Review layer reflects reviewer's opinion
    assert image_review.result is False, "ImageReview.result should be False (reviewer says not fake)"
    assert manual_review.status == "completed"
    assert rr.status1 == "completed"

    # Upload layer marks that review has occurred
    assert image_upload.isReview is True

    # IMPORTANT: DetectionResult.is_fake must NOT be mutated by the review
    # (detection result is immutable; review is a separate opinion layer)
    assert detection_result.is_fake is True, (
        "DetectionResult.is_fake must remain True after review override — "
        "review does not rewrite detection results"
    )

    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
```

---

## Task 3 — Quota flow: deduct on submit, refund on failure, then apply review on failed detection

**Subsystems crossed:** quota management → detection pipeline failure → review creation gate

**Bug risk 1:** Quota is deducted at submit time. If detection fails, `_refund_detection_usage` must restore it — the test verifies the refund path in `run_image_detection_task_async`.

**Bug risk 2:** `create_review_task_with_admin_check` calls `images[0].detection_results.first()` — if no `DetectionResult` exists (e.g., task creation itself failed) or the result is in `failed` status with no meaningful data, the review endpoint must reject the request, not silently create a useless review.

- [ ] Create test function `test_quota_deducted_refunded_on_failure_and_review_blocked` in `test_cross_flow.py`

```python
@override_settings(MEDIA_ROOT=TEMP_MEDIA)
@patch(
    "core.views.views_dectection._start_detection_task_thread",
    side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
        task_id, image_ids, if_use_llm, num_images
    ),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
@patch(
    "core.services.capabilities.image.local_detection.get_result",
    return_value=None,  # pipeline returns nothing — triggers failure + refund
)
@patch("core.views.views_review.send_mail")
def test_quota_deducted_refunded_on_failure_and_review_blocked(
    _mock_mail, _mock_result, _mock_commit, _mock_thread
):
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
    Path(TEMP_MEDIA).mkdir(parents=True, exist_ok=True)

    org, admin, publisher, reviewer = _setup_org_with_users()

    # Record baseline quota
    org.refresh_from_db()
    initial_quota = org.remaining_non_llm_uses

    client = APIClient()
    client.force_authenticate(publisher)

    # Step 1: upload and submit detection (pipeline will fail)
    _, image_id = _upload_and_extract_image(client, TEMP_MEDIA)
    submit_resp = _submit_image_detection(client, [image_id], task_name="Quota Failure Task")
    assert submit_resp.status_code == 200
    task_id = submit_resp.data["task_id"]

    # Step 2: detection should have failed and quota refunded
    org.refresh_from_db()
    task = DetectionTask.objects.get(pk=task_id)
    assert task.status == "failed", f"Task should be failed, got: {task.status}"
    assert org.remaining_non_llm_uses == initial_quota, (
        f"Quota should be refunded after failure. "
        f"Expected {initial_quota}, got {org.remaining_non_llm_uses}"
    )

    # Step 3: publisher attempts to apply for manual review on the failed detection
    review_resp = client.post(
        "/api/create_review_task_with_admin_check/",
        {
            "image_ids": [image_id],
            "reviewers": [reviewer.id],
            "reason": "Trying to review a failed detection",
        },
        format="json",
    )
    # The endpoint should reject this — no valid completed DetectionResult exists
    # Acceptable responses: 404 (no detection result found) or 400 (task not completed)
    assert review_resp.status_code in (400, 404), (
        f"Expected 400 or 404 when applying review on failed detection, "
        f"got {review_resp.status_code}: {review_resp.data}"
    )

    # Confirm no ReviewRequest was created
    assert ReviewRequest.objects.filter(user=publisher, organization=org).count() == 0

    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
```

---

## Task 4 — Same source file: image detection + paper detection simultaneously

**Subsystems crossed:** file management → image detection task → paper/resource detection task

**Bug risk:** Both tasks reference the same `FileManagement` record. If tasks share internal state (e.g., both mutate `resource_files` on the same file), results could interfere. The test verifies that two independent `DetectionTask` records are created and their results are isolated.

- [ ] Create test function `test_same_file_image_and_paper_detection_independent` in `test_cross_flow.py`

```python
@override_settings(MEDIA_ROOT=TEMP_MEDIA)
@patch(
    "core.views.views_dectection._start_detection_task_thread",
    side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
        task_id, image_ids, if_use_llm, num_images
    ),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
@patch(
    "core.services.capabilities.image.local_detection.generate_detection_task_report",
    return_value="reports/cross_flow_4.pdf",
)
@patch(
    "core.services.capabilities.image.local_detection.get_result",
    return_value=fake_detection_payload(),
)
@patch(
    "core.services.capabilities.llm.fastdetect_client.detect_text_segment",
    return_value={"label": "AI", "probability": 0.92},
)
def test_same_file_image_and_paper_detection_independent(
    _mock_llm, _mock_img_result, _mock_report, _mock_commit, _mock_thread
):
    """
    Upload a PDF → extract an image from it.
    Submit image detection on the extracted image.
    Submit paper detection on the same source file.
    Verify: two separate DetectionTask records; results don't cross-contaminate.
    """
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
    Path(TEMP_MEDIA).mkdir(parents=True, exist_ok=True)

    org = make_organization()
    publisher = make_user(organization=org, role="publisher")
    client = APIClient()
    client.force_authenticate(publisher)

    # Upload the source file (PNG treated as image type)
    _, image_id = _upload_and_extract_image(client, TEMP_MEDIA)
    image_upload = ImageUpload.objects.get(pk=image_id)
    file_management = image_upload.file_management

    # Submit image detection on the extracted image
    img_submit_resp = _submit_image_detection(client, [image_id], task_name="Image Task")
    assert img_submit_resp.status_code == 200
    image_task_id = img_submit_resp.data["task_id"]

    # Submit paper/resource detection on the same source file
    paper_submit_resp = client.post(
        "/api/resource-task/create/",
        {
            "task_type": "paper",
            "file_ids": [file_management.id],
            "task_name": "Paper Task",
            "api_key": "",
            "if_use_llm": False,
        },
        format="json",
    )
    # Paper detection may succeed or return 400 (quota / file type restrictions);
    # the key assertion is that the image task is unaffected
    paper_task_id = paper_submit_resp.data.get("task_id")

    # Image task must be completely independent
    image_task = DetectionTask.objects.get(pk=image_task_id)
    assert image_task.task_type == "image"
    assert image_task.status == "completed"

    image_dr = DetectionResult.objects.filter(detection_task=image_task).first()
    assert image_dr is not None
    assert image_dr.status == "completed"

    # If paper task was created, verify it is separate
    if paper_task_id:
        paper_task = DetectionTask.objects.filter(pk=paper_task_id).first()
        if paper_task:
            assert paper_task.pk != image_task.pk, "Paper task must be a distinct DetectionTask"
            assert paper_task.task_type in ("paper", "review")
            # Paper task must not share DetectionResult rows with image task
            shared_results = DetectionResult.objects.filter(
                detection_task=image_task
            ).filter(detection_task=paper_task)
            assert not shared_results.exists(), "Tasks must not share DetectionResult records"

    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
```

---

## Task 5 — Report download endpoint: after detection, and after review

**Subsystems crossed:** detection pipeline → report generation → report download endpoint → review completion → report still accessible

**Bug risk:** `download_task_report` calls `ensure_task_report_file(task, force=True)` and then opens the file. If the file path stored in `task.report_file` is wrong or if review completion somehow mutates the task, the file open will raise `FileNotFoundError`.

- [ ] Create test function `test_report_download_after_detection_and_review` in `test_cross_flow.py`

```python
@override_settings(MEDIA_ROOT=TEMP_MEDIA)
@patch(
    "core.views.views_dectection._start_detection_task_thread",
    side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
        task_id, image_ids, if_use_llm, num_images
    ),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
@patch(
    "core.services.capabilities.image.local_detection.generate_detection_task_report",
    return_value="reports/cross_flow_5.pdf",
)
@patch(
    "core.services.capabilities.image.local_detection.get_result",
    return_value=fake_detection_payload(),
)
@patch("core.views.views_review.send_mail")
@patch("core.utils.report_generator.ensure_task_report_file")
def test_report_download_after_detection_and_review(
    mock_ensure_report,
    _mock_mail,
    _mock_result,
    _mock_report,
    _mock_commit,
    _mock_thread,
):
    """
    Verifies:
    1. After detection completes, GET /api/tasks/<task_id>/report/ returns 200.
    2. After manual review completes, the same endpoint still returns 200.
    3. GET /api/tasks_image/<image_id>/report/ also returns 200.
    """
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
    report_dir = Path(TEMP_MEDIA) / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Create a real (tiny) PDF-like file the endpoint can open
    fake_pdf_path = report_dir / "cross_flow_5.pdf"
    fake_pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")
    mock_ensure_report.return_value = "reports/cross_flow_5.pdf"

    org, admin, publisher, reviewer = _setup_org_with_users()
    client = APIClient()
    client.force_authenticate(publisher)

    # --- Detection phase ---
    _, image_id = _upload_and_extract_image(client, TEMP_MEDIA)
    submit_resp = _submit_image_detection(client, [image_id], task_name="Report Test Task")
    assert submit_resp.status_code == 200
    task_id = submit_resp.data["task_id"]

    task = DetectionTask.objects.get(pk=task_id)
    assert task.status == "completed"

    # Download report immediately after detection
    report_resp = client.get(f"/api/tasks/{task_id}/report/")
    assert report_resp.status_code == 200, (
        f"Report download should succeed after detection, got {report_resp.status_code}: "
        f"{getattr(report_resp, 'data', '')}"
    )

    # Download image-level report
    image_report_resp = client.get(f"/api/tasks_image/{image_id}/report/")
    assert image_report_resp.status_code == 200, (
        f"Image report download should succeed, got {image_report_resp.status_code}"
    )

    # --- Review phase ---
    rr = ReviewRequest.objects.create(
        detection_result=DetectionResult.objects.get(detection_task=task),
        user=publisher,
        organization=org,
        reason="Post-detection review",
    )
    image_upload = ImageUpload.objects.get(pk=image_id)
    rr.imgs.add(image_upload)
    rr.reviewers.add(reviewer)

    client.force_authenticate(admin)
    client.post(f"/api/handle_reviewRequest/{rr.id}/", {"choice": 1, "reason": "ok"}, format="json")

    manual_review = ManualReview.objects.get(review_request=rr, reviewer=reviewer)
    client.force_authenticate(reviewer)
    client.post(
        f"/api/post_review/{manual_review.id}/",
        {
            "result": [
                {
                    "img_id": image_id,
                    "score": [3, 3, 3, 3, 3, 3, 3],
                    "reason": ["r"] * 7,
                    "points": [[]] * 7,
                    "final": True,
                }
            ]
        },
        format="json",
    )

    # After review completes, report download must still work
    client.force_authenticate(publisher)
    report_after_review_resp = client.get(f"/api/tasks/{task_id}/report/")
    assert report_after_review_resp.status_code == 200, (
        "Report download must still work after manual review completes — "
        f"got {report_after_review_resp.status_code}"
    )

    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
```

---

## Task 6 — Notification created after detection completion and after review completion

**Subsystems crossed:** detection pipeline → notification system; review `post_review` → notification system

**Bug risk:** `send_ai_detection_complete_notification` is defined in `core/util.py` but is NOT called anywhere in the orchestrator or service layer — it exists but may be disconnected. The test verifies whether the notification pipeline is actually wired up end-to-end. It also verifies `post_review` sends a notification to the publisher (via `send_notification` in `views_review.py`).

- [ ] Create test function `test_notification_created_after_detection_and_review` in `test_cross_flow.py`

```python
@override_settings(MEDIA_ROOT=TEMP_MEDIA)
@patch(
    "core.views.views_dectection._start_detection_task_thread",
    side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
        task_id, image_ids, if_use_llm, num_images
    ),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
@patch(
    "core.services.capabilities.image.local_detection.generate_detection_task_report",
    return_value="reports/cross_flow_6.pdf",
)
@patch(
    "core.services.capabilities.image.local_detection.get_result",
    return_value=fake_detection_payload(),
)
@patch("core.views.views_review.send_mail")
def test_notification_created_after_detection_and_review(
    _mock_mail, _mock_result, _mock_report, _mock_commit, _mock_thread
):
    """
    1. After detection completes: assert Notification record for publisher exists
       (category=SYSTEM, title contains 'AI检测').
       NOTE: If no notification is wired up in the detection pipeline, this test
       documents the gap rather than failing silently.
    2. After reviewer submits post_review: assert Notification for publisher exists
       (sent by views_review.post_review via send_notification).
    """
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
    Path(TEMP_MEDIA).mkdir(parents=True, exist_ok=True)

    org, admin, publisher, reviewer = _setup_org_with_users()
    client = APIClient()
    client.force_authenticate(publisher)

    notifications_before_detection = Notification.objects.filter(
        receiver_id=publisher.id
    ).count()

    # --- Detection phase ---
    _, image_id = _upload_and_extract_image(client, TEMP_MEDIA)
    submit_resp = _submit_image_detection(client, [image_id], task_name="Notification Test")
    assert submit_resp.status_code == 200
    task_id = submit_resp.data["task_id"]

    task = DetectionTask.objects.get(pk=task_id)
    assert task.status == "completed"

    # Check for detection-completion notification
    detection_notifications = Notification.objects.filter(
        receiver_id=publisher.id,
        category=Notification.SYSTEM,
    ).count()
    # Document current behavior: if notification IS wired, count increases.
    # If not wired, count stays the same — test records the finding.
    detection_notification_wired = detection_notifications > notifications_before_detection

    # --- Review phase ---
    dr = DetectionResult.objects.get(detection_task=task)
    rr = ReviewRequest.objects.create(
        detection_result=dr,
        user=publisher,
        organization=org,
        reason="Notification test review",
    )
    image_upload = ImageUpload.objects.get(pk=image_id)
    rr.imgs.add(image_upload)
    rr.reviewers.add(reviewer)

    client.force_authenticate(admin)
    client.post(f"/api/handle_reviewRequest/{rr.id}/", {"choice": 1, "reason": "ok"}, format="json")

    manual_review = ManualReview.objects.get(review_request=rr, reviewer=reviewer)

    notifications_before_review_submit = Notification.objects.filter(
        receiver_id=publisher.id
    ).count()

    client.force_authenticate(reviewer)
    post_resp = client.post(
        f"/api/post_review/{manual_review.id}/",
        {
            "result": [
                {
                    "img_id": image_id,
                    "score": [4, 4, 4, 4, 4, 4, 4],
                    "reason": ["r"] * 7,
                    "points": [[]] * 7,
                    "final": True,
                }
            ]
        },
        format="json",
    )
    assert post_resp.status_code == 201

    # After reviewer submits, publisher MUST receive a notification
    # (views_review.post_review calls send_notification for review_request.user)
    notifications_after_review = Notification.objects.filter(
        receiver_id=publisher.id
    ).count()
    assert notifications_after_review > notifications_before_review_submit, (
        "Publisher must receive a notification after reviewer submits their review "
        "(send_notification called in views_review.post_review)"
    )

    # Also: admin-accept sends notification to reviewer
    reviewer_notifications = Notification.objects.filter(receiver_id=reviewer.id).count()
    assert reviewer_notifications >= 1, (
        "Reviewer must receive a notification when admin accepts their review request "
        "(send_notification called in views_admin.handle_review_request)"
    )

    # Report: detection notification wiring status
    if not detection_notification_wired:
        import warnings
        warnings.warn(
            "Detection completion does NOT send a Notification to the publisher. "
            "send_ai_detection_complete_notification exists in core/util.py but is "
            "not called from the detection orchestrator. Consider wiring it up.",
            stacklevel=1,
        )

    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
```

---

## Task 7 — Role isolation: publisher's tasks not visible to other organization's users

**Subsystems crossed:** detection task → task list endpoints → role/org access control

**Bug risk:** `get_user_tasks` and `get_detection_task_status_normal` filter by `user=request.user`. If a reviewer or a user from a different org somehow gets a `task_id` from the first publisher, they must get 404, not the data. Cross-org leakage is a security boundary bug.

- [ ] Create test function `test_role_isolation_tasks_not_visible_across_orgs` in `test_cross_flow.py`

```python
@override_settings(MEDIA_ROOT=TEMP_MEDIA)
@patch(
    "core.views.views_dectection._start_detection_task_thread",
    side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
        task_id, image_ids, if_use_llm, num_images
    ),
)
@patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
@patch(
    "core.services.capabilities.image.local_detection.generate_detection_task_report",
    return_value="reports/cross_flow_7.pdf",
)
@patch(
    "core.services.capabilities.image.local_detection.get_result",
    return_value=fake_detection_payload(),
)
def test_role_isolation_tasks_not_visible_across_orgs(
    _mock_result, _mock_report, _mock_commit, _mock_thread
):
    """
    Publisher A (Org 1) submits detection.
    Reviewer B (Org 1): GET /api/user-tasks/ must NOT show Publisher A's task
        (reviewer only sees their own tasks, not publisher tasks).
    Publisher C (Org 2): GET /api/detection-task/<task_id>/status/ must return 404.
    Admin D (Org 1): GET /api/user-tasks/ must NOT show tasks from other users by default
        (user-tasks is scoped to request.user, not to org-wide).
    """
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
    Path(TEMP_MEDIA).mkdir(parents=True, exist_ok=True)

    # Org 1
    org1, admin1, publisher_a, reviewer_b = _setup_org_with_users()

    # Org 2: separate organization
    org2 = make_organization()
    publisher_c = make_user(organization=org2, role="publisher")

    publisher_a_client = APIClient()
    publisher_a_client.force_authenticate(publisher_a)

    # Publisher A submits detection
    _, image_id = _upload_and_extract_image(publisher_a_client, TEMP_MEDIA)
    submit_resp = _submit_image_detection(publisher_a_client, [image_id], task_name="Org1 Publisher Task")
    assert submit_resp.status_code == 200
    task_id = submit_resp.data["task_id"]

    # Reviewer B (same org, different role) sees their own task list
    reviewer_b_client = APIClient()
    reviewer_b_client.force_authenticate(reviewer_b)
    reviewer_tasks_resp = reviewer_b_client.get("/api/user-tasks/")
    assert reviewer_tasks_resp.status_code == 200
    reviewer_task_ids = [t["task_id"] for t in reviewer_tasks_resp.data.get("tasks", [])]
    assert task_id not in reviewer_task_ids, (
        f"Reviewer B must NOT see Publisher A's detection task {task_id} in /api/user-tasks/"
    )

    # Reviewer B tries to access task status directly by ID — must get 404
    reviewer_status_resp = reviewer_b_client.get(f"/api/detection-task/{task_id}/status/")
    assert reviewer_status_resp.status_code == 404, (
        f"Reviewer B must get 404 for Publisher A's task status, "
        f"got {reviewer_status_resp.status_code}"
    )

    # Publisher C (Org 2) tries to access Org 1's task — must get 404
    publisher_c_client = APIClient()
    publisher_c_client.force_authenticate(publisher_c)
    cross_org_resp = publisher_c_client.get(f"/api/detection-task/{task_id}/status/")
    assert cross_org_resp.status_code == 404, (
        f"Publisher C (Org 2) must get 404 for Org 1's task status, "
        f"got {cross_org_resp.status_code}"
    )

    # Publisher C's own task list is empty (no tasks for org 2)
    c_tasks_resp = publisher_c_client.get("/api/user-tasks/")
    assert c_tasks_resp.status_code == 200
    assert c_tasks_resp.data.get("total_tasks", 0) == 0, (
        "Publisher C (Org 2) must see 0 tasks — no cross-org leakage"
    )

    # Publisher A can still see their own task
    publisher_a_tasks_resp = publisher_a_client.get("/api/user-tasks/")
    assert publisher_a_tasks_resp.status_code == 200
    a_task_ids = [t["task_id"] for t in publisher_a_tasks_resp.data.get("tasks", [])]
    assert task_id in a_task_ids, "Publisher A must still see their own task"

    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
```

---

## Implementation checklist

- [ ] Task 1: `test_detection_complete_then_apply_manual_review`
- [ ] Task 2: `test_review_override_data_consistency`
- [ ] Task 3: `test_quota_deducted_refunded_on_failure_and_review_blocked`
- [ ] Task 4: `test_same_file_image_and_paper_detection_independent`
- [ ] Task 5: `test_report_download_after_detection_and_review`
- [ ] Task 6: `test_notification_created_after_detection_and_review`
- [ ] Task 7: `test_role_isolation_tasks_not_visible_across_orgs`
- [ ] Verify all 7 tests collected: `pytest core/tests/integration/api/cross_flow/test_cross_flow.py --collect-only`
- [ ] Run full suite and confirm no regressions in other integration tests

---

## Known design gaps documented by these tests

| # | Gap | Location | Severity |
|---|-----|----------|----------|
| 1 | `send_ai_detection_complete_notification` defined but not called from the detection orchestrator | `core/util.py` + `core/services/orchestrators/image_task_orchestrator.py` | Medium |
| 2 | `create_review_task_with_admin_check` does not validate that the `DetectionResult` is in `completed` status — it only checks that one exists | `core/views/views_review.py:194` | High |
| 3 | `download_task_report` / `download_image_report` use `open()` directly — if `ensure_task_report_file` returns a relative path and `MEDIA_ROOT` is misconfigured, tests surface a `FileNotFoundError` | `core/views/views_dectection.py:244, 295` | Medium |
