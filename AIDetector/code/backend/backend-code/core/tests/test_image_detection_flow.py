import base64
import pickle
import shutil
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from core import call_figure_detection
from core.call_figure_detection import _run_local_inference
from core.local_detection import (
    _create_batch_inputs,
    _extract_single_result,
    _persist_detection_result,
    _run_local_detection_batch,
)
from core.models import (
    DetectionResult,
    DetectionTask,
    FileManagement,
    ImageUpload,
    Organization,
    SubDetectionResult,
    User,
)
from core.views.views_dectection import (
    _run_detection_task_async,
    get_detection_task_status_normal,
    submit_detection2,
)


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


@override_settings(ENABLE_FANYI=False)
class LocalDetectionFlowTests(TestCase):
    def setUp(self):
        temp_root = Path.home() / ".codex" / "memories" / "buaa-se-aid-test-media"
        shutil.rmtree(temp_root, ignore_errors=True)
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_media = str(temp_root)
        self.override = override_settings(MEDIA_ROOT=self.temp_media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.temp_media, ignore_errors=True))

        self.factory = APIRequestFactory()
        self.organization = Organization.objects.create(name="Org", email="org@example.com")
        self.user = User.objects.create_user(
            username="publisher",
            email="publisher@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )
        self.file_record = FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name="source.pdf",
            file_size=128,
            file_type="pdf",
            resource_type="image",
            stored_path="uploads/source.pdf",
            tag="Other",
        )
        image_name, image_bytes = build_test_image()
        extracted_dir = Path(self.temp_media) / "extracted_images"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        image_path = extracted_dir / image_name
        image_path.write_bytes(image_bytes)
        self.image_upload = ImageUpload.objects.create(
            file_management=self.file_record,
            image=f"extracted_images/{image_name}",
        )

    def submit_detection(self, task_name="Local Detection"):
        request = self.factory.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [self.image_upload.id],
                "task_name": task_name,
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        force_authenticate(request, user=self.user)
        return submit_detection2(request)

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.local_detection.generate_detection_task_report", return_value="reports/task_1_report.pdf")
    @patch("core.local_detection.get_result", return_value=fake_detection_payload())
    def test_submit_detection_runs_local_pipeline_and_updates_results(
        self, _mock_result, _mock_report, _mock_on_commit, _mock_thread
    ):
        response = self.submit_detection()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["execution_mode"], "local_async")
        self.assertEqual(response.data["status"], "in_progress")

        detection_result = DetectionResult.objects.get(image_upload=self.image_upload)
        self.assertEqual(detection_result.status, "completed")
        self.assertTrue(detection_result.is_fake)
        self.assertTrue(detection_result.exif_photoshop)

        refreshed_upload = ImageUpload.objects.get(pk=self.image_upload.pk)
        self.assertTrue(refreshed_upload.isDetect)
        self.assertTrue(refreshed_upload.isFake)
        self.assertEqual(SubDetectionResult.objects.filter(detection_result=detection_result).count(), 5)

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.local_detection.generate_detection_task_report", return_value="reports/task_1_report.pdf")
    @patch("core.local_detection.get_result", return_value=fake_detection_payload())
    def test_task_status_endpoint_reports_completed_task(self, _mock_result, _mock_report, _mock_on_commit, _mock_thread):
        submit_response = self.submit_detection("Status Check")
        task_id = submit_response.data["task_id"]

        status_request = self.factory.get(f"/api/detection-task/{task_id}/status/")
        force_authenticate(status_request, user=self.user)
        status_response = get_detection_task_status_normal(status_request, task_id)

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data["status"], "completed")
        self.assertEqual(status_response.data["task_type"], "image")
        self.assertFalse(status_response.data["is_running"])
        self.assertEqual(status_response.data["progress"]["total_results"], 1)
        self.assertEqual(status_response.data["progress"]["completed_results"], 1)
        self.assertEqual(status_response.data["progress"]["pending_results"], 0)
        self.assertEqual(len(status_response.data["detection_results"]), 1)

    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.views.views_dectection._start_detection_task_thread")
    def test_submit_detection_returns_quickly_with_in_progress_task_state(self, _mock_thread, _mock_on_commit):
        response = self.submit_detection("Queued Detection")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["execution_mode"], "local_async")
        self.assertEqual(response.data["status"], "in_progress")

        task = DetectionTask.objects.get(task_name="Queued Detection")
        self.assertEqual(task.status, "in_progress")
        self.assertEqual(DetectionResult.objects.filter(detection_task=task, status="in_progress").count(), 1)
        _mock_thread.assert_called_once()

    def test_create_batch_inputs_writes_zip_and_json_for_selected_images(self):
        task = DetectionTask.objects.create(
            organization=self.organization,
            user=self.user,
            task_type="image",
            task_name="Batch Build",
            status="pending",
            cmd_block_size=64,
            urn_k=0.3,
            if_use_llm=False,
        )
        detection_result = DetectionResult.objects.create(
            image_upload=self.image_upload,
            detection_task=task,
            status="in_progress",
        )

        batch_dir = _create_batch_inputs(task, 0, [detection_result])
        self.addCleanup(lambda: shutil.rmtree(batch_dir, ignore_errors=True))

        self.assertTrue((batch_dir / "img.zip").exists())
        self.assertTrue((batch_dir / "data.json").exists())

    @patch("core.local_detection.fanyi_text", side_effect=lambda text: text)
    def test_persist_detection_result_marks_upload_and_creates_sub_results(self, _mock_translate):
        task = DetectionTask.objects.create(
            organization=self.organization,
            user=self.user,
            task_type="image",
            task_name="Persist Result",
            status="in_progress",
        )
        detection_result = DetectionResult.objects.create(
            image_upload=self.image_upload,
            detection_task=task,
            status="in_progress",
        )

        parsed_result = {
            "llm_text": "synthetic analysis",
            "llm_img": None,
            "ela": np.full((12, 12), 20, dtype=np.uint8),
            "overall_is_fake": True,
            "overall_confidence": 0.85,
            "exif_flags": {"photoshop": True, "time_modified": False},
            "sub_method_results": [
                {"method": "splicing", "prob": 0.85, "mask": np.ones((12, 12), dtype=np.float32).tolist()},
                {"method": "blurring", "prob": 0.10, "mask": np.zeros((12, 12), dtype=np.float32).tolist()},
            ],
        }

        _persist_detection_result(detection_result, parsed_result)

        detection_result.refresh_from_db()
        self.image_upload.refresh_from_db()
        self.assertEqual(detection_result.status, "completed")
        self.assertTrue(detection_result.is_fake)
        self.assertEqual(detection_result.llm_judgment, "synthetic analysis")
        self.assertTrue(self.image_upload.isDetect)
        self.assertTrue(self.image_upload.isFake)
        self.assertEqual(SubDetectionResult.objects.filter(detection_result=detection_result).count(), 2)

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.views.views_dectection.execute_detection_task", side_effect=RuntimeError("pipeline crashed"))
    def test_submit_detection_marks_task_failed_when_pipeline_raises(self, _mock_execute, _mock_on_commit, _mock_thread):
        response = self.submit_detection("Failure Path")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["execution_mode"], "local_async")

        task = DetectionTask.objects.get(task_name="Failure Path")
        self.assertEqual(task.status, "failed")
        self.assertEqual(task.error_message, "pipeline crashed")
        self.assertIsNotNone(task.completion_time)

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.views.views_dectection.execute_detection_task", side_effect=RuntimeError("pipeline crashed"))
    def test_task_status_endpoint_reports_failed_task(self, _mock_execute, _mock_on_commit, _mock_thread):
        submit_response = self.submit_detection("Failed Status")
        task_id = submit_response.data["task_id"]

        status_request = self.factory.get(f"/api/detection-task/{task_id}/status/")
        force_authenticate(status_request, user=self.user)
        status_response = get_detection_task_status_normal(status_request, task_id)

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data["status"], "failed")
        self.assertFalse(status_response.data["is_running"])
        self.assertEqual(status_response.data["result_summary"], "pipeline crashed")
        self.assertEqual(status_response.data["error_message"], "pipeline crashed")


class LocalDetectionParsingTests(TestCase):
    def test_extract_single_result_parses_payload_shape_used_by_local_service(self):
        parsed = _extract_single_result(fake_detection_payload(), 0)

        self.assertTrue(parsed["overall_is_fake"])
        self.assertEqual(parsed["overall_confidence"], 1.0)
        self.assertEqual(parsed["llm_text"], "")
        self.assertTrue(parsed["exif_flags"]["photoshop"])
        self.assertFalse(parsed["exif_flags"]["time_modified"])
        self.assertEqual(len(parsed["sub_method_results"]), 5)
        self.assertEqual(parsed["sub_method_results"][0]["method"], "splicing")
        self.assertEqual(parsed["sub_method_results"][0]["prob"], 0.85)


@override_settings(ENABLE_FANYI=False)
class LocalBridgeTests(TestCase):
    def setUp(self):
        temp_root = Path.home() / ".codex" / "memories" / "buaa-se-aid-test-media-bridge"
        shutil.rmtree(temp_root, ignore_errors=True)
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_media = str(temp_root)
        self.override = override_settings(MEDIA_ROOT=self.temp_media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.temp_media, ignore_errors=True))

    @patch("core.call_figure_detection.subprocess.run")
    def test_run_local_inference_decodes_pickled_payload_from_stdout(self, mock_run):
        expected_payload = fake_detection_payload()
        encoded_payload = base64.b64encode(pickle.dumps(expected_payload)).decode("utf-8")
        mock_run.return_value = SimpleNamespace(
            returncode=0,
            stdout=f"booting\nstart results\n{encoded_payload}\n".encode("utf-8"),
            stderr=b"",
        )

        result = _run_local_inference()

        self.assertEqual(result[0][0], "llm")
        self.assertEqual(result[1][0], "ela")
        self.assertEqual(len(result), len(expected_payload))

    @patch("core.local_detection.generate_detection_task_report", return_value="reports/task_report.pdf")
    @patch("core.local_detection.fanyi_text", side_effect=lambda text: text)
    def test_run_local_detection_batch_with_fake_ai_service_process(self, _mock_translate, _mock_report):
        organization = Organization.objects.create(name="Bridge E2E Org", email="bridge-e2e@example.com")
        user = User.objects.create_user(
            username="bridge-e2e-user",
            email="bridge-e2e-user@example.com",
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
            task_name="Bridge E2E",
            status="pending",
            cmd_block_size=64,
            urn_k=0.3,
            if_use_llm=False,
        )

        extracted_dir = Path(self.temp_media) / "extracted_images"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        image1_name, image1_bytes = build_test_image("bridge_image_1.png", color=(255, 0, 0))
        image2_name, image2_bytes = build_test_image("bridge_image_2.png", color=(0, 255, 0))
        (extracted_dir / image1_name).write_bytes(image1_bytes)
        (extracted_dir / image2_name).write_bytes(image2_bytes)

        image1 = ImageUpload.objects.create(file_management=file_record, image=f"extracted_images/{image1_name}")
        image2 = ImageUpload.objects.create(file_management=file_record, image=f"extracted_images/{image2_name}")
        detection_result_for_image2 = DetectionResult.objects.create(
            image_upload=image2,
            detection_task=task,
            status="in_progress",
        )
        detection_result_for_image1 = DetectionResult.objects.create(
            image_upload=image1,
            detection_task=task,
            status="in_progress",
        )

        batch_dir = _create_batch_inputs(task, 0, [detection_result_for_image2, detection_result_for_image1])
        self.addCleanup(lambda: shutil.rmtree(batch_dir, ignore_errors=True))

        fake_service_root = Path(__file__).resolve().parents[1] / "test_fixtures"
        fake_shared_root = fake_service_root / "shared"
        fake_entrypoint = fake_service_root / "fake_ai_service_entrypoint.py"
        shutil.rmtree(fake_shared_root, ignore_errors=True)
        self.addCleanup(lambda: shutil.rmtree(fake_shared_root, ignore_errors=True))

        with patch.object(call_figure_detection, "AI_SERVICE_DIR", fake_service_root), patch.object(
            call_figure_detection, "AI_SERVICE_ENTRYPOINT", fake_entrypoint
        ), patch.object(call_figure_detection, "AI_SERVICE_PYTHON", sys.executable), patch.object(
            call_figure_detection, "AI_SERVICE_TEST_DIR", fake_shared_root
        ), patch.object(call_figure_detection, "AI_SERVICE_TMP_DIR", fake_service_root / "tmp"), patch.object(
            call_figure_detection, "AI_SERVICE_TORCH_HOME", fake_service_root / "torch"
        ):
            _run_local_detection_batch(
                detection_result_ids=[detection_result_for_image2.id, detection_result_for_image1.id],
                batch_dir=batch_dir,
                image_num=2,
                task_pk=task.pk,
            )

        image1.refresh_from_db()
        image2.refresh_from_db()
        dr1 = DetectionResult.objects.get(image_upload=image1, detection_task=task)
        dr2 = DetectionResult.objects.get(image_upload=image2, detection_task=task)
        task.refresh_from_db()

        self.assertEqual(task.status, "completed")
        self.assertFalse(image1.isFake)
        self.assertTrue(image2.isFake)
        self.assertIn("00000001.png", dr1.llm_judgment)
        self.assertIn("00000002.png", dr2.llm_judgment)
        self.assertEqual(dr1.status, "completed")
        self.assertEqual(dr2.status, "completed")
        self.assertEqual(SubDetectionResult.objects.filter(detection_result=dr1).count(), 5)
        self.assertEqual(SubDetectionResult.objects.filter(detection_result=dr2).count(), 5)

    @patch("core.local_detection.generate_detection_task_report", return_value="reports/task_report.pdf")
    @patch("core.local_detection.fanyi_text", side_effect=lambda text: text)
    @patch("core.local_detection.get_result", return_value=fake_detection_payload_for_two_images())
    def test_run_local_detection_batch_should_map_results_by_image_order(self, _mock_result, _mock_translate, _mock_report):
        organization = Organization.objects.create(name="Bridge Org", email="bridge@example.com")
        user = User.objects.create_user(
            username="bridge-user",
            email="bridge-user@example.com",
            password="pass123456",
            role="publisher",
            organization=organization,
        )
        file_record = FileManagement.objects.create(
            user=user,
            organization=organization,
            file_name="source.pdf",
            file_size=256,
            file_type="pdf",
            resource_type="image",
            stored_path="uploads/source.pdf",
            tag="Other",
        )
        task = DetectionTask.objects.create(
            organization=organization,
            user=user,
            task_type="image",
            task_name="Ordering Check",
            status="pending",
            cmd_block_size=64,
            urn_k=0.3,
            if_use_llm=False,
        )

        extracted_dir = Path(self.temp_media) / "extracted_images"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        image1_name, image1_bytes = build_test_image("image_1.png", color=(255, 0, 0))
        image2_name, image2_bytes = build_test_image("image_2.png", color=(0, 255, 0))
        (extracted_dir / image1_name).write_bytes(image1_bytes)
        (extracted_dir / image2_name).write_bytes(image2_bytes)

        image1 = ImageUpload.objects.create(file_management=file_record, image=f"extracted_images/{image1_name}")
        image2 = ImageUpload.objects.create(file_management=file_record, image=f"extracted_images/{image2_name}")

        detection_result_for_image2 = DetectionResult.objects.create(
            image_upload=image2,
            detection_task=task,
            status="in_progress",
        )
        detection_result_for_image1 = DetectionResult.objects.create(
            image_upload=image1,
            detection_task=task,
            status="in_progress",
        )

        batch_dir = _create_batch_inputs(task, 0, [detection_result_for_image2, detection_result_for_image1])
        self.addCleanup(lambda: shutil.rmtree(batch_dir, ignore_errors=True))

        _run_local_detection_batch(
            detection_result_ids=[detection_result_for_image2.id, detection_result_for_image1.id],
            batch_dir=batch_dir,
            image_num=2,
            task_pk=task.pk,
        )

        image1.refresh_from_db()
        image2.refresh_from_db()
        self.assertFalse(image1.isFake)
        self.assertTrue(image2.isFake)


@override_settings(ENABLE_FANYI=False)
class LocalDetectionApiCoverageTests(TestCase):
    def setUp(self):
        temp_root = Path.home() / ".codex" / "memories" / "buaa-se-aid-test-media-api"
        shutil.rmtree(temp_root, ignore_errors=True)
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_media = str(temp_root)
        self.override = override_settings(MEDIA_ROOT=self.temp_media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.temp_media, ignore_errors=True))

        self.client = APIClient()
        self.organization = Organization.objects.create(name="API Org", email="api-org@example.com")
        self.user = User.objects.create_user(
            username="api-publisher",
            email="api-publisher@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )
        self.client.force_authenticate(self.user)

    def upload_image_via_api(self, name="upload.png", color=(255, 0, 0)):
        image_name, image_bytes = build_test_image(name, color=color)
        uploaded_file = SimpleUploadedFile(image_name, image_bytes, content_type="image/png")
        response = self.client.post(
            "/api/upload/",
            {"detection_type": "image", "file": uploaded_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        return response.data["file_id"]

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.local_detection.generate_detection_task_report", return_value="reports/task_report.pdf")
    @patch("core.local_detection.get_result", return_value=fake_detection_payload())
    def test_upload_detect_and_read_results_through_api(
        self, _mock_result, _mock_report, _mock_on_commit, _mock_thread
    ):
        file_id = self.upload_image_via_api()

        extracted_response = self.client.get(f"/api/upload/{file_id}/extract_images/")
        self.assertEqual(extracted_response.status_code, 200)
        self.assertEqual(extracted_response.data["total"], 1)
        image_id = extracted_response.data["images"][0]["image_id"]

        submit_response = self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [image_id],
                "task_name": "API Full Chain",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        self.assertEqual(submit_response.status_code, 200)
        task_id = submit_response.data["task_id"]

        tasks_response = self.client.get("/api/user-tasks/")
        self.assertEqual(tasks_response.status_code, 200)
        self.assertEqual(tasks_response.data["total_tasks"], 1)
        self.assertEqual(tasks_response.data["tasks"][0]["status"], "completed")
        self.assertEqual(tasks_response.data["tasks"][0]["result_summary"], "疑似造假 1/1")

        task_detail_response = self.client.get(f"/api/detection-task/{task_id}/status/")
        self.assertEqual(task_detail_response.status_code, 200)
        self.assertEqual(task_detail_response.data["status"], "completed")
        self.assertFalse(task_detail_response.data["is_running"])
        self.assertEqual(task_detail_response.data["progress"]["completed_results"], 1)
        self.assertEqual(task_detail_response.data["progress"]["pending_results"], 0)
        self.assertEqual(task_detail_response.data["progress"]["failed_results"], 0)

        fake_results_response = self.client.get(f"/api/tasks/{task_id}/fake_results/?include_image=1")
        self.assertEqual(fake_results_response.status_code, 200)
        self.assertEqual(fake_results_response.data["total_results"], 1)

        normal_results_response = self.client.get(f"/api/tasks/{task_id}/normal_results/?include_image=1")
        self.assertEqual(normal_results_response.status_code, 200)
        self.assertEqual(normal_results_response.data["total_results"], 0)

        image_result_response = self.client.get(f"/api/results_image/{image_id}/")
        self.assertEqual(image_result_response.status_code, 200)
        self.assertTrue(image_result_response.data["overall"]["is_fake"])
        self.assertIn("sub_methods", image_result_response.data)

        detection_result_id_response = self.client.get(f"/api/tasks_image/{image_id}/getdr/")
        self.assertEqual(detection_result_id_response.status_code, 200)
        result_id = detection_result_id_response.data["detection_result_id"]

        result_detail_response = self.client.get(f"/api/results/{result_id}/")
        self.assertEqual(result_detail_response.status_code, 200)
        self.assertTrue(result_detail_response.data["overall"]["is_fake"])
        self.assertEqual(len(result_detail_response.data["sub_methods"]), 5)

    @patch(
        "core.views.views_dectection._start_detection_task_thread",
        side_effect=lambda task_id, image_ids, if_use_llm, num_images: _run_detection_task_async(
            task_id, image_ids, if_use_llm, num_images
        ),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.local_detection.get_result", return_value=None)
    def test_failed_local_detection_is_reported_as_failed_everywhere_and_refunds_usage(
        self, _mock_result, _mock_on_commit, _mock_thread
    ):
        file_id = self.upload_image_via_api(name="broken.png", color=(0, 255, 0))
        image_id = self.client.get(f"/api/upload/{file_id}/extract_images/").data["images"][0]["image_id"]
        initial_remaining = self.organization.remaining_non_llm_uses

        submit_response = self.client.post(
            "/api/detection/submit/",
            {
                "mode": 1,
                "image_ids": [image_id],
                "task_name": "API Failure Chain",
                "cmd_block_size": 64,
                "urn_k": 0.3,
                "if_use_llm": False,
            },
            format="json",
        )
        self.assertEqual(submit_response.status_code, 200)
        task_id = submit_response.data["task_id"]

        self.organization.refresh_from_db()
        self.assertEqual(self.organization.remaining_non_llm_uses, initial_remaining)

        task = DetectionTask.objects.get(pk=task_id)
        self.assertEqual(task.status, "failed")
        self.assertIn("did not return a result payload", task.error_message)

        detection_result = DetectionResult.objects.get(detection_task=task, image_upload_id=image_id)
        self.assertEqual(detection_result.status, "failed")

        tasks_response = self.client.get("/api/user-tasks/")
        self.assertEqual(tasks_response.status_code, 200)
        self.assertEqual(tasks_response.data["tasks"][0]["status"], "failed")
        self.assertIn("did not return a result payload", tasks_response.data["tasks"][0]["error_message"])

        task_detail_response = self.client.get(f"/api/detection-task/{task_id}/status/")
        self.assertEqual(task_detail_response.status_code, 200)
        self.assertEqual(task_detail_response.data["status"], "failed")
        self.assertFalse(task_detail_response.data["is_running"])
        self.assertEqual(task_detail_response.data["progress"]["completed_results"], 0)
        self.assertEqual(task_detail_response.data["progress"]["pending_results"], 0)
        self.assertEqual(task_detail_response.data["progress"]["failed_results"], 1)
        self.assertEqual(task_detail_response.data["detection_results"][0]["status"], "failed")

        image_detection_response = self.client.get(f"/api/detection/{image_id}/")
        self.assertEqual(image_detection_response.status_code, 500)
        self.assertEqual(image_detection_response.data["status"], "检测失败")
