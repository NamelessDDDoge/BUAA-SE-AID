import base64
import os
import pickle
import shutil
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import (
    DetectionResult,
    DetectionTask,
    FileManagement,
    ImageUpload,
    Organization,
    SubDetectionResult,
    User,
)
from core.services.capabilities.image import local_inference_client
from core.services.capabilities.image.local_detection import (
    _create_batch_inputs,
    _run_local_detection_batch,
)
from core.views.views_dectection import _run_detection_task_async


def build_test_image(name="test.png", color=(255, 0, 0)):
    buffer = BytesIO()
    Image.new("RGB", (12, 12), color=color).save(buffer, format="PNG")
    return name, buffer.getvalue()


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


def fake_detection_payload_for_two_images():
    """image_1 → authentic (prob=0.10), image_2 → tampered (prob=0.95)."""
    return [
        ("llm", [("image_1.png", ("authentic", None)), ("image_2.png", ("tampered", None))]),
        (
            "ela",
            [
                ("image_1.png", np.full((12, 12), 1, dtype=np.uint8)),
                ("image_2.png", np.full((12, 12), 2, dtype=np.uint8)),
            ],
        ),
        ("exif", [("image_1.png", None), ("image_2.png", None)]),
        ("cmd", []),
        ("urn_coarse_v2", [np.zeros((12, 12), dtype=np.float32), 0.10, np.ones((12, 12), dtype=np.float32), 0.95]),
        ("urn_blurring", [np.zeros((12, 12), dtype=np.float32), 0.10, np.zeros((12, 12), dtype=np.float32), 0.10]),
        ("urn_brute_force", [np.zeros((12, 12), dtype=np.float32), 0.10, np.zeros((12, 12), dtype=np.float32), 0.10]),
        ("urn_contrast", [np.zeros((12, 12), dtype=np.float32), 0.10, np.zeros((12, 12), dtype=np.float32), 0.10]),
        ("urn_inpainting", [np.zeros((12, 12), dtype=np.float32), 0.10, np.zeros((12, 12), dtype=np.float32), 0.10]),
    ]


@pytest.mark.django_db
class TestFullUploadDetectResultsChain:
    """
    Fast tier — single image.
    Upload → extract → detect → poll status → read result detail → user task list.
    All assertions check the INTERACTION between components; single-unit behavior is
    already covered in test_image_detection_flow.py.
    """

    @pytest.fixture(autouse=True)
    def setup(self, settings, tmp_path):
        settings.ENABLE_FANYI = False
        settings.MEDIA_ROOT = str(tmp_path / "media")
        self.media_root = settings.MEDIA_ROOT
        Path(self.media_root).mkdir(parents=True, exist_ok=True)

        self.client = APIClient()
        self.organization = Organization.objects.create(
            name="Chain Org", email="chain-org@example.com"
        )
        self.user = User.objects.create_user(
            username="chain-user",
            email="chain-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )
        self.client.force_authenticate(self.user)

    def _upload_image(self, name="upload.png", color=(255, 0, 0)):
        _, image_bytes = build_test_image(name, color=color)
        uploaded_file = SimpleUploadedFile(name, image_bytes, content_type="image/png")
        response = self.client.post(
            "/api/upload/",
            {"detection_type": "image", "file": uploaded_file},
            format="multipart",
        )
        assert response.status_code == 200, f"Upload failed: {response.data}"
        return response.data["file_id"]

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch(
        "core.services.capabilities.image.local_detection.generate_detection_task_report",
        return_value="reports/chain_report.pdf",
    )
    @patch(
        "core.services.capabilities.image.local_detection.get_result",
        return_value=fake_detection_payload(),
    )
    def test_full_chain_single_image_all_hand_offs_correct(
        self, _mock_result, _mock_report, _mock_on_commit, _mock_thread
    ):
        # Step 1: upload file
        file_id = self._upload_image()

        # Step 2: extract images — must return exactly 1 image
        extract_resp = self.client.get(f"/api/upload/{file_id}/extract_images/")
        assert extract_resp.status_code == 200
        assert extract_resp.data["total"] == 1
        image_id = extract_resp.data["images"][0]["image_id"]

        # Verify ImageUpload exists with the correct file management link
        image_upload = ImageUpload.objects.get(pk=image_id)
        assert image_upload.file_management.id == file_id

        # Step 3: submit detection
        submit_resp = self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [image_id],
                "task_name": "Chain Single Image",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        assert submit_resp.status_code == 200
        task_id = submit_resp.data["task_id"]
        # The submit response must echo back the image that was submitted
        assert image_id in submit_resp.data["image_ids"]

        # Step 4: poll task status — must reflect completed pipeline
        status_resp = self.client.get(f"/api/detection-task/{task_id}/status/")
        assert status_resp.status_code == 200
        status_data = status_resp.data
        assert status_data["status"] == "completed"
        assert status_data["is_running"] is False
        assert status_data["progress"]["total_results"] == 1
        assert status_data["progress"]["completed_results"] == 1
        assert status_data["progress"]["pending_results"] == 0
        assert status_data["progress"]["failed_results"] == 0

        # The status endpoint must link back to the CORRECT image_id
        image_results = status_data["results"]["image_results"]
        assert len(image_results) == 1
        assert image_results[0]["image_id"] == image_id

        # Step 5: read per-image result via /api/results_image/<image_id>/
        result_resp = self.client.get(f"/api/results_image/{image_id}/")
        assert result_resp.status_code == 200
        result_data = result_resp.data
        assert result_data["overall"]["is_fake"] is True
        assert "sub_methods" in result_data
        assert len(result_data["sub_methods"]) == 5  # 5 URN sub-results

        # Step 6: user task list shows this task as completed
        tasks_resp = self.client.get("/api/user-tasks/")
        assert tasks_resp.status_code == 200
        assert tasks_resp.data["total_tasks"] == 1
        task_summary = tasks_resp.data["tasks"][0]
        assert task_summary["status"] == "completed"
        # The summary string must mention the fake count
        assert "1/1" in task_summary["result_summary"]


@pytest.mark.django_db
class TestMultiImageBatchOrdering:
    """
    Fast tier — two images.
    Payload: image_1 → authentic (prob=0.10), image_2 → tampered (prob=0.95).
    After pipeline, image_1.isFake must be False and image_2.isFake must be True.
    Verifies the interaction between _create_batch_inputs ordering,
    AI payload indexing, and _run_local_detection_batch result assignment.
    """

    @pytest.fixture(autouse=True)
    def setup(self, settings, tmp_path):
        settings.ENABLE_FANYI = False
        settings.MEDIA_ROOT = str(tmp_path / "media")
        self.media_root = settings.MEDIA_ROOT
        Path(self.media_root).mkdir(parents=True, exist_ok=True)

        self.organization = Organization.objects.create(
            name="Ordering Org", email="ordering-org@example.com"
        )
        self.user = User.objects.create_user(
            username="ordering-user",
            email="ordering-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )
        self.file_record = FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name="source.pdf",
            file_size=256,
            file_type="pdf",
            resource_type="image",
            stored_path="uploads/source.pdf",
            tag="Other",
        )
        # Write actual image files so _create_batch_inputs can read them
        extracted_dir = Path(self.media_root) / "extracted_images"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        for fname, color in [("image_1.png", (255, 0, 0)), ("image_2.png", (0, 255, 0))]:
            _, img_bytes = build_test_image(fname, color=color)
            (extracted_dir / fname).write_bytes(img_bytes)

        self.image1 = ImageUpload.objects.create(
            file_management=self.file_record,
            image="extracted_images/image_1.png",
        )
        self.image2 = ImageUpload.objects.create(
            file_management=self.file_record,
            image="extracted_images/image_2.png",
        )
        self.task = DetectionTask.objects.create(
            organization=self.organization,
            user=self.user,
            task_type="image",
            task_name="Ordering Check",
            status="pending",
            cmd_block_size=64,
            urn_k=0.3,
            if_use_llm=False,
        )

    @patch(
        "core.services.capabilities.image.local_detection.generate_detection_task_report",
        return_value="reports/order_report.pdf",
    )
    @patch(
        "core.services.capabilities.image.local_detection.fanyi_text",
        side_effect=lambda text: text,
    )
    @patch(
        "core.services.capabilities.image.local_detection.get_result",
        return_value=fake_detection_payload_for_two_images(),
    )
    def test_result_for_image1_is_authentic_and_image2_is_tampered(
        self, _mock_result, _mock_translate, _mock_report
    ):
        """
        DetectionResult records are intentionally created in reverse image order
        (image2 first, image1 second) to simulate the real insertion ordering bug.
        The pipeline must still assign payloads by position in the batch zip —
        image_1.png at index 0 → authentic, image_2.png at index 1 → tampered.
        """
        # Create results in REVERSED insertion order (potential ordering bug trigger)
        dr_image2 = DetectionResult.objects.create(
            image_upload=self.image2,
            detection_task=self.task,
            status="in_progress",
        )
        dr_image1 = DetectionResult.objects.create(
            image_upload=self.image1,
            detection_task=self.task,
            status="in_progress",
        )

        batch_dir = _create_batch_inputs(self.task, 0, [dr_image2, dr_image1])

        _run_local_detection_batch(
            detection_result_ids=[dr_image2.id, dr_image1.id],
            batch_dir=batch_dir,
            image_num=2,
            task_pk=self.task.pk,
        )

        self.image1.refresh_from_db()
        self.image2.refresh_from_db()
        dr_image1.refresh_from_db()
        dr_image2.refresh_from_db()

        # Core ordering assertion: image_1 was authentic, image_2 was tampered
        assert self.image1.isFake is False, (
            f"BUG: image_1 was classified as fake (isFake={self.image1.isFake}). "
            "Results were mapped to the wrong images."
        )
        assert self.image2.isFake is True, (
            f"BUG: image_2 was not classified as tampered (isFake={self.image2.isFake}). "
            "Results were mapped to the wrong images."
        )
        assert dr_image1.status == "completed"
        assert dr_image2.status == "completed"

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch(
        "core.services.capabilities.image.local_detection.generate_detection_task_report",
        return_value="reports/order_api_report.pdf",
    )
    @patch(
        "core.services.capabilities.image.local_detection.get_result",
        return_value=fake_detection_payload_for_two_images(),
    )
    def test_status_endpoint_image_results_map_to_correct_images_after_batch(
        self, _mock_result, _mock_report, _mock_on_commit, _mock_thread
    ):
        """
        After a two-image batch completes through the API, the status endpoint
        must return each image result keyed to the correct image_id.
        image_1 → is_fake=False, image_2 → is_fake=True.
        """
        from rest_framework.test import APIClient as _APIClient
        client = _APIClient()
        client.force_authenticate(self.user)

        submit_resp = client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [self.image1.id, self.image2.id],
                "task_name": "Ordering API Check",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        assert submit_resp.status_code == 200

        # There should be one task per image (create_image_detection_tasks splits them)
        task_ids = submit_resp.data["task_ids"]
        assert len(task_ids) == 2

        # Verify each task's status endpoint reports correct is_fake mapping
        results_by_image = {}
        for task_id in task_ids:
            status_resp = client.get(f"/api/detection-task/{task_id}/status/")
            assert status_resp.status_code == 200
            for img_result in status_resp.data["results"]["image_results"]:
                results_by_image[img_result["image_id"]] = img_result["is_fake"]

        assert results_by_image.get(self.image1.id) is False, (
            "BUG: image_1 (authentic) should not be marked fake via status endpoint"
        )
        assert results_by_image.get(self.image2.id) is True, (
            "BUG: image_2 (tampered) should be marked fake via status endpoint"
        )


@pytest.mark.django_db
class TestDetectionFailureQuotaRefund:
    """
    Fast tier.
    When the AI pipeline fails (get_result returns None), the system must:
      1. Mark DetectionTask.status == "failed"
      2. Refund the consumed quota (organization.remaining_non_llm_uses restored)
      3. All result-facing endpoints show "failed" consistently
    Tests deliberately do NOT fix any bug — they assert the expected contract
    and will FAIL if quota is not refunded or status is inconsistent.
    """

    @pytest.fixture(autouse=True)
    def setup(self, settings, tmp_path):
        settings.ENABLE_FANYI = False
        settings.MEDIA_ROOT = str(tmp_path / "media")
        Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)

        self.client = APIClient()
        self.organization = Organization.objects.create(
            name="Quota Org", email="quota-org@example.com"
        )
        self.user = User.objects.create_user(
            username="quota-user",
            email="quota-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )
        self.client.force_authenticate(self.user)

    def _upload_and_extract(self, name="broken.png", color=(0, 255, 0)):
        _, image_bytes = build_test_image(name, color=color)
        upload_resp = self.client.post(
            "/api/upload/",
            {"detection_type": "image", "file": SimpleUploadedFile(name, image_bytes, content_type="image/png")},
            format="multipart",
        )
        assert upload_resp.status_code == 200
        file_id = upload_resp.data["file_id"]
        extract_resp = self.client.get(f"/api/upload/{file_id}/extract_images/")
        assert extract_resp.status_code == 200
        return extract_resp.data["images"][0]["image_id"]

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch(
        "core.services.capabilities.image.local_detection.get_result",
        return_value=None,  # Simulate AI service returning no payload
    )
    def test_quota_is_refunded_when_pipeline_fails(
        self, _mock_result, _mock_on_commit, _mock_thread
    ):
        image_id = self._upload_and_extract()

        self.organization.refresh_from_db()
        quota_before = self.organization.remaining_non_llm_uses

        submit_resp = self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [image_id],
                "task_name": "Quota Refund Test",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        assert submit_resp.status_code == 200
        task_id = submit_resp.data["task_id"]

        # Quota must be restored after pipeline failure
        self.organization.refresh_from_db()
        quota_after = self.organization.remaining_non_llm_uses
        assert quota_after == quota_before, (
            f"BUG: Quota was not refunded after pipeline failure. "
            f"Before: {quota_before}, After: {quota_after}"
        )

        # Task must be marked failed
        task = DetectionTask.objects.get(pk=task_id)
        assert task.status == "failed", f"BUG: task.status={task.status!r}, expected 'failed'"
        assert task.error_message, "BUG: error_message should be non-empty on failure"

        # DetectionResult must be failed
        dr = DetectionResult.objects.get(detection_task=task, image_upload_id=image_id)
        assert dr.status == "failed"

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch(
        "core.services.capabilities.image.local_detection.get_result",
        return_value=None,
    )
    def test_all_result_endpoints_consistently_show_failed_after_pipeline_error(
        self, _mock_result, _mock_on_commit, _mock_thread
    ):
        image_id = self._upload_and_extract(name="broken2.png", color=(0, 0, 255))

        submit_resp = self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [image_id],
                "task_name": "Failure Consistency",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        task_id = submit_resp.data["task_id"]

        # /api/user-tasks/ must show failed
        tasks_resp = self.client.get("/api/user-tasks/")
        assert tasks_resp.status_code == 200
        task_entry = next(
            (t for t in tasks_resp.data["tasks"] if t["task_id"] == task_id), None
        )
        assert task_entry is not None, "Task not found in user-tasks list"
        assert task_entry["status"] == "failed", (
            f"BUG: user-tasks shows status={task_entry['status']!r}, expected 'failed'"
        )

        # /api/detection-task/<id>/status/ must show failed with is_running=False
        status_resp = self.client.get(f"/api/detection-task/{task_id}/status/")
        assert status_resp.status_code == 200
        sd = status_resp.data
        assert sd["status"] == "failed"
        assert sd["is_running"] is False
        assert sd["progress"]["failed_results"] == 1
        assert sd["progress"]["completed_results"] == 0

        # /api/detection/<image_id>/ must return 500 (detection failed)
        img_status_resp = self.client.get(f"/api/detection/{image_id}/")
        assert img_status_resp.status_code == 500
        assert img_status_resp.data["status"] == "检测失败"


@pytest.mark.django_db
class TestRepeatedDetectionOnSameImage:
    """
    Fast tier.
    Tests what happens when the same image_id is submitted for detection twice.
    Verifies that the second submission creates a NEW task and NEW DetectionResult,
    does NOT re-use or overwrite the first result, and both tasks have independent
    status endpoints.
    """

    @pytest.fixture(autouse=True)
    def setup(self, settings, tmp_path):
        settings.ENABLE_FANYI = False
        settings.MEDIA_ROOT = str(tmp_path / "media")
        Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)

        self.client = APIClient()
        self.organization = Organization.objects.create(
            name="Repeat Org", email="repeat-org@example.com"
        )
        self.user = User.objects.create_user(
            username="repeat-user",
            email="repeat-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )
        self.client.force_authenticate(self.user)

    def _upload_and_extract(self):
        _, image_bytes = build_test_image("repeat.png", color=(128, 64, 32))
        upload_resp = self.client.post(
            "/api/upload/",
            {"detection_type": "image", "file": SimpleUploadedFile("repeat.png", image_bytes, content_type="image/png")},
            format="multipart",
        )
        assert upload_resp.status_code == 200
        file_id = upload_resp.data["file_id"]
        extract_resp = self.client.get(f"/api/upload/{file_id}/extract_images/")
        assert extract_resp.status_code == 200
        return extract_resp.data["images"][0]["image_id"]

    def _submit(self, image_id, task_name):
        return self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [image_id],
                "task_name": task_name,
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch(
        "core.services.capabilities.image.local_detection.generate_detection_task_report",
        return_value="reports/repeat_report.pdf",
    )
    @patch(
        "core.services.capabilities.image.local_detection.get_result",
        return_value=fake_detection_payload(),
    )
    def test_second_submission_creates_independent_task_and_result(
        self, _mock_result, _mock_report, _mock_on_commit, _mock_thread
    ):
        image_id = self._upload_and_extract()

        # First submission
        resp1 = self._submit(image_id, "First Run")
        assert resp1.status_code == 200
        task_id_1 = resp1.data["task_id"]

        # Verify first task completed
        dr_count_after_first = DetectionResult.objects.filter(image_upload_id=image_id).count()
        assert dr_count_after_first == 1

        # Second submission on the same image
        resp2 = self._submit(image_id, "Second Run")
        assert resp2.status_code == 200, (
            f"BUG: Second submission on already-detected image was rejected. "
            f"status={resp2.status_code}, data={resp2.data}"
        )
        task_id_2 = resp2.data["task_id"]

        assert task_id_1 != task_id_2, "BUG: Both submissions returned the same task_id"

        # Each task must have exactly 1 DetectionResult (NOT shared)
        dr_for_task1 = DetectionResult.objects.filter(
            detection_task_id=task_id_1, image_upload_id=image_id
        )
        dr_for_task2 = DetectionResult.objects.filter(
            detection_task_id=task_id_2, image_upload_id=image_id
        )
        assert dr_for_task1.count() == 1, (
            f"BUG: task 1 has {dr_for_task1.count()} DetectionResults for this image"
        )
        assert dr_for_task2.count() == 1, (
            f"BUG: task 2 has {dr_for_task2.count()} DetectionResults for this image"
        )

        # Both task status endpoints must be independent
        status1 = self.client.get(f"/api/detection-task/{task_id_1}/status/")
        status2 = self.client.get(f"/api/detection-task/{task_id_2}/status/")
        assert status1.status_code == 200
        assert status2.status_code == 200
        assert status1.data["status"] == "completed"
        assert status2.data["status"] == "completed"

        # ImageUpload.isDetect must be True after both runs
        image_upload = ImageUpload.objects.get(pk=image_id)
        assert image_upload.isDetect is True

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch(
        "core.services.capabilities.image.local_detection.generate_detection_task_report",
        return_value="reports/repeat_report2.pdf",
    )
    @patch(
        "core.services.capabilities.image.local_detection.get_result",
        return_value=fake_detection_payload(),
    )
    def test_user_tasks_list_shows_both_submissions(
        self, _mock_result, _mock_report, _mock_on_commit, _mock_thread
    ):
        image_id = self._upload_and_extract()

        self._submit(image_id, "Run Alpha")
        self._submit(image_id, "Run Beta")

        tasks_resp = self.client.get("/api/user-tasks/")
        assert tasks_resp.status_code == 200
        total = tasks_resp.data["total_tasks"]
        assert total == 2, (
            f"BUG: Expected 2 tasks in user-tasks (one per submission), got {total}"
        )
        statuses = {t["task_name"]: t["status"] for t in tasks_resp.data["tasks"]}
        assert statuses.get("Run Alpha") == "completed"
        assert statuses.get("Run Beta") == "completed"


@pytest.mark.django_db
class TestBridgeTierFullPipeline:
    """
    Bridge tier — uses the real fake_ai_service_entrypoint.py subprocess.
    Tests the full path: _create_batch_inputs → subprocess → stdout decode →
    _persist_detection_result. Two images are submitted in intentionally
    reversed insertion order to expose ordering bugs that mocks cannot catch.
    """

    @pytest.fixture(autouse=True)
    def setup(self, settings, tmp_path):
        settings.ENABLE_FANYI = False
        settings.MEDIA_ROOT = str(tmp_path / "media")
        self.media_root = settings.MEDIA_ROOT
        Path(self.media_root).mkdir(parents=True, exist_ok=True)

        self.remote_url_patch = patch.object(local_inference_client, "AI_REMOTE_INFER_URL", "")
        self.remote_env_patch = patch.dict(os.environ, {"AI_REMOTE_INFER_URL": ""})
        self.remote_url_patch.start()
        self.remote_env_patch.start()

        yield

        self.remote_url_patch.stop()
        self.remote_env_patch.stop()

    @patch(
        "core.services.capabilities.image.local_detection.generate_detection_task_report",
        return_value="reports/bridge_report.pdf",
    )
    @patch(
        "core.services.capabilities.image.local_detection.fanyi_text",
        side_effect=lambda text: text,
    )
    def test_bridge_two_images_results_assigned_correctly_by_zip_ordering(
        self, _mock_translate, _mock_report
    ):
        """
        The fake AI service assigns:
          - index 0 (first name alphabetically in zip) → prob=0.10 (authentic)
          - index 1 (second name alphabetically in zip) → prob=0.95 (tampered)
        After pipeline: image at sorted position 0 must be authentic, position 1 must be fake.
        Reversed DB insertion order is used to trigger the ordering bug if present.
        """
        organization = Organization.objects.create(
            name="Bridge E2E Org 2", email="bridge2@example.com"
        )
        user = User.objects.create_user(
            username="bridge2-user",
            email="bridge2-user@example.com",
            password="pass123456",
            role="publisher",
            organization=organization,
        )
        file_record = FileManagement.objects.create(
            user=user,
            organization=organization,
            file_name="source.pdf",
            file_size=512,
            file_type="pdf",
            resource_type="image",
            stored_path="uploads/source.pdf",
            tag="Other",
        )
        task = DetectionTask.objects.create(
            organization=organization,
            user=user,
            task_type="image",
            task_name="Bridge Full Pipeline",
            status="pending",
            cmd_block_size=64,
            urn_k=0.3,
            if_use_llm=False,
        )

        extracted_dir = Path(self.media_root) / "extracted_images"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        _, img1_bytes = build_test_image("bridge_image_1.png", color=(255, 0, 0))
        _, img2_bytes = build_test_image("bridge_image_2.png", color=(0, 255, 0))
        (extracted_dir / "bridge_image_1.png").write_bytes(img1_bytes)
        (extracted_dir / "bridge_image_2.png").write_bytes(img2_bytes)

        image1 = ImageUpload.objects.create(
            file_management=file_record,
            image="extracted_images/bridge_image_1.png",
        )
        image2 = ImageUpload.objects.create(
            file_management=file_record,
            image="extracted_images/bridge_image_2.png",
        )

        # Intentionally reversed insertion order
        dr2 = DetectionResult.objects.create(
            image_upload=image2, detection_task=task, status="in_progress"
        )
        dr1 = DetectionResult.objects.create(
            image_upload=image1, detection_task=task, status="in_progress"
        )

        batch_dir = _create_batch_inputs(task, 0, [dr2, dr1])

        fake_service_root = Path(__file__).resolve().parents[3] / "fixtures"
        fake_shared_root = fake_service_root / "shared_bridge2"
        fake_entrypoint = fake_service_root / "fake_ai_service_entrypoint.py"
        shutil.rmtree(fake_shared_root, ignore_errors=True)

        try:
            with (
                patch.object(local_inference_client, "AI_SERVICE_DIR", fake_service_root),
                patch.object(local_inference_client, "AI_SERVICE_ENTRYPOINT", fake_entrypoint),
                patch.object(local_inference_client, "AI_SERVICE_PYTHON", sys.executable),
                patch.object(local_inference_client, "AI_SERVICE_TEST_DIR", fake_shared_root),
                patch.object(local_inference_client, "AI_SERVICE_TMP_DIR", fake_service_root / "tmp2"),
                patch.object(local_inference_client, "AI_SERVICE_TORCH_HOME", fake_service_root / "torch2"),
            ):
                _run_local_detection_batch(
                    detection_result_ids=[dr2.id, dr1.id],
                    batch_dir=batch_dir,
                    image_num=2,
                    task_pk=task.pk,
                )
        finally:
            shutil.rmtree(fake_shared_root, ignore_errors=True)

        image1.refresh_from_db()
        image2.refresh_from_db()
        dr1.refresh_from_db()
        dr2.refresh_from_db()
        task.refresh_from_db()

        assert task.status == "completed"
        assert dr1.status == "completed"
        assert dr2.status == "completed"

        # The fake service assigns prob=0.10 to index 0, 0.95 to index 1.
        # bridge_image_1.png sorts before bridge_image_2.png → image1 is authentic.
        assert image1.isFake is False, (
            "BUG: bridge_image_1 (index 0, authentic) was marked as fake. "
            "Result ordering in the batch pipeline is broken."
        )
        assert image2.isFake is True, (
            "BUG: bridge_image_2 (index 1, tampered) was not marked as fake."
        )
        assert SubDetectionResult.objects.filter(detection_result=dr1).count() == 5
        assert SubDetectionResult.objects.filter(detection_result=dr2).count() == 5


@pytest.mark.django_db
class TestTaskStatusConsistency:
    """
    Fast tier.
    Verifies that is_running, status, and detection_results in the status endpoint
    are consistent across task lifecycle states: pending → in_progress → completed/failed.
    """

    @pytest.fixture(autouse=True)
    def setup(self, settings, tmp_path):
        settings.ENABLE_FANYI = False
        settings.MEDIA_ROOT = str(tmp_path / "media")
        Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)

        self.client = APIClient()
        self.organization = Organization.objects.create(
            name="Status Org", email="status-org@example.com"
        )
        self.user = User.objects.create_user(
            username="status-user",
            email="status-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )
        self.client.force_authenticate(self.user)

        # Write a real image file for ImageUpload
        extracted_dir = Path(settings.MEDIA_ROOT) / "extracted_images"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        _, img_bytes = build_test_image("status_img.png")
        (extracted_dir / "status_img.png").write_bytes(img_bytes)

        self.file_record = FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name="status.pdf",
            file_size=128,
            file_type="pdf",
            resource_type="image",
            stored_path="uploads/status.pdf",
            tag="Other",
        )
        self.image_upload = ImageUpload.objects.create(
            file_management=self.file_record,
            image="extracted_images/status_img.png",
        )

    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.views.views_dectection._start_detection_task_thread")
    def test_is_running_true_while_task_is_pending(self, _mock_thread, _mock_on_commit):
        """
        When _start_detection_task_thread is mocked to do nothing (thread never runs),
        the task stays in 'pending' state. The status endpoint must return is_running=True.
        The detection_results list must already be populated (pending state) with status='pending'.
        """
        submit_resp = self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [self.image_upload.id],
                "task_name": "Pending State",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        assert submit_resp.status_code == 200
        task_id = submit_resp.data["task_id"]

        status_resp = self.client.get(f"/api/detection-task/{task_id}/status/")
        assert status_resp.status_code == 200
        sd = status_resp.data

        assert sd["is_running"] is True, (
            f"BUG: is_running should be True for pending task, got {sd['is_running']}"
        )
        assert sd["status"] == "pending"

        # detection_results must be populated even in pending state
        assert len(sd["detection_results"]) == 1, (
            "BUG: detection_results list should have 1 entry even in pending state"
        )
        assert sd["detection_results"][0]["status"] == "pending"

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch(
        "core.services.capabilities.image.local_detection.generate_detection_task_report",
        return_value="reports/status_report.pdf",
    )
    @patch(
        "core.services.capabilities.image.local_detection.get_result",
        return_value=fake_detection_payload(),
    )
    def test_is_running_false_and_results_populated_after_completion(
        self, _mock_result, _mock_report, _mock_on_commit, _mock_thread
    ):
        submit_resp = self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [self.image_upload.id],
                "task_name": "Completed State",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        task_id = submit_resp.data["task_id"]

        status_resp = self.client.get(f"/api/detection-task/{task_id}/status/")
        sd = status_resp.data

        assert sd["is_running"] is False
        assert sd["status"] == "completed"
        assert sd["progress"]["completed_results"] == 1
        assert sd["progress"]["pending_results"] == 0

        # Ensure detection_results contains the completed entry
        assert len(sd["detection_results"]) == 1
        assert sd["detection_results"][0]["status"] == "completed"

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.views.views_dectection.execute_detection_task", side_effect=RuntimeError("task crashed"))
    def test_is_running_false_on_failed_task(self, _mock_exec, _mock_on_commit, _mock_thread):
        submit_resp = self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [self.image_upload.id],
                "task_name": "Failed State",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        task_id = submit_resp.data["task_id"]

        status_resp = self.client.get(f"/api/detection-task/{task_id}/status/")
        sd = status_resp.data

        assert sd["is_running"] is False, (
            f"BUG: is_running should be False for failed task, got {sd['is_running']}"
        )
        assert sd["status"] == "failed"
        assert sd["error_message"] == "task crashed"


@pytest.mark.django_db
class TestReportDownloadAfterDetection:
    """
    Fast tier.
    After detection completes, GET /api/tasks/<task_id>/report/ must:
      - Return a file download (200, Content-Disposition: attachment)
      - Work even when called immediately after detection without manual report generation
    Also tests: downloading report for an incomplete task returns 400.
    """

    @pytest.fixture(autouse=True)
    def setup(self, settings, tmp_path):
        settings.ENABLE_FANYI = False
        settings.MEDIA_ROOT = str(tmp_path / "media")
        self.media_root = settings.MEDIA_ROOT
        Path(self.media_root).mkdir(parents=True, exist_ok=True)

        self.client = APIClient()
        self.organization = Organization.objects.create(
            name="Report Org", email="report-org@example.com"
        )
        self.user = User.objects.create_user(
            username="report-user",
            email="report-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )
        self.client.force_authenticate(self.user)

    def _upload_and_get_image_id(self, name="report_img.png"):
        _, image_bytes = build_test_image(name)
        upload_resp = self.client.post(
            "/api/upload/",
            {"detection_type": "image", "file": SimpleUploadedFile(name, image_bytes, content_type="image/png")},
            format="multipart",
        )
        assert upload_resp.status_code == 200
        file_id = upload_resp.data["file_id"]
        extract_resp = self.client.get(f"/api/upload/{file_id}/extract_images/")
        assert extract_resp.status_code == 200
        return extract_resp.data["images"][0]["image_id"]

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch(
        "core.services.capabilities.image.local_detection.generate_detection_task_report",
        return_value="reports/final_report.pdf",
    )
    @patch(
        "core.services.capabilities.image.local_detection.get_result",
        return_value=fake_detection_payload(),
    )
    def test_report_download_returns_200_after_completed_detection(
        self, _mock_result, _mock_report, _mock_on_commit, _mock_thread
    ):
        image_id = self._upload_and_get_image_id()

        submit_resp = self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [image_id],
                "task_name": "Report Download Test",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        task_id = submit_resp.data["task_id"]

        # Write a real PDF stub so FileResponse can open it
        reports_dir = Path(self.media_root) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "final_report.pdf").write_bytes(b"%PDF-1.4 stub content")

        # Also mock ensure_task_report_file to return the path we just created
        with patch(
            "core.views.views_dectection.ensure_task_report_file",
            return_value="reports/final_report.pdf",
        ):
            report_resp = self.client.get(f"/api/tasks/{task_id}/report/")

        assert report_resp.status_code == 200, (
            f"BUG: report download returned {report_resp.status_code}. "
            f"Expected 200 (FileResponse). data={getattr(report_resp, 'data', 'streaming')}"
        )
        content_disp = report_resp.get("Content-Disposition", "")
        assert "attachment" in content_disp, (
            f"BUG: Content-Disposition should indicate attachment, got: {content_disp!r}"
        )
        assert f"task_{task_id}_report.pdf" in content_disp

    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.views.views_dectection._start_detection_task_thread")
    def test_report_download_returns_400_for_pending_task(
        self, _mock_thread, _mock_on_commit
    ):
        image_id = self._upload_and_get_image_id(name="pending_img.png")

        submit_resp = self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [image_id],
                "task_name": "Pending Report Test",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        task_id = submit_resp.data["task_id"]

        report_resp = self.client.get(f"/api/tasks/{task_id}/report/")
        assert report_resp.status_code == 400, (
            f"BUG: Downloading report for pending task should return 400, got {report_resp.status_code}"
        )
        assert "not completed" in report_resp.data.get("detail", "").lower(), (
            f"Expected 'not completed' in error detail, got: {report_resp.data}"
        )

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch(
        "core.services.capabilities.image.local_detection.generate_detection_task_report",
        return_value="reports/image_report.pdf",
    )
    @patch(
        "core.services.capabilities.image.local_detection.get_result",
        return_value=fake_detection_payload(),
    )
    def test_image_level_report_download_via_tasks_image_endpoint(
        self, _mock_result, _mock_report, _mock_on_commit, _mock_thread
    ):
        """
        GET /api/tasks_image/<image_id>/report/ must also serve the task report PDF
        after detection completes on that image.
        """
        image_id = self._upload_and_get_image_id(name="image_report.png")

        submit_resp = self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [image_id],
                "task_name": "Image Report Download",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        assert submit_resp.status_code == 200

        reports_dir = Path(self.media_root) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "image_report.pdf").write_bytes(b"%PDF-1.4 image report stub")

        with patch(
            "core.views.views_dectection.ensure_task_report_file",
            return_value="reports/image_report.pdf",
        ):
            report_resp = self.client.get(f"/api/tasks_image/{image_id}/report/")

        assert report_resp.status_code == 200, (
            f"BUG: image-level report download returned {report_resp.status_code}"
        )
        content_disp = report_resp.get("Content-Disposition", "")
        assert "attachment" in content_disp
