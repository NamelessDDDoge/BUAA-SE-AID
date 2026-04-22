import shutil
from pathlib import Path
from unittest.mock import patch

import fitz
import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import DetectionTask, FileManagement, Organization, User
from core.services.orchestrators.resource_task_orchestrator import (
    create_resource_detection_task,
    run_resource_detection_task_async,
)


REPO_TASK_7_REPORT = Path(__file__).resolve().parents[6] / "task_7_report.pdf"


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


class MockFastDetectResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"data": {"prob": 0.1, "details": {"source": "mock"}}}


@override_settings(ENABLE_FANYI=False)
class ResourceTaskFlowTests(TestCase):
    def setUp(self):
        temp_root = Path.home() / ".codex" / "memories" / "buaa-se-aid-resource-task-tests"
        shutil.rmtree(temp_root, ignore_errors=True)
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_media = str(temp_root)
        self.override = override_settings(MEDIA_ROOT=self.temp_media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.temp_media, ignore_errors=True))

        self.client = APIClient()
        self.organization = Organization.objects.create(name="Resource Org", email="resource-org@example.com")
        self.user = User.objects.create_user(
            username="resource-user",
            email="resource-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )
        self.client.force_authenticate(self.user)

    def create_file(self, file_name, resource_type, linked_file=None):
        return FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name=file_name,
            file_size=256,
            file_type="application/octet-stream",
            resource_type=resource_type,
            stored_path=f"uploads/{file_name}",
            linked_file=linked_file,
        )

    @patch("core.views.views_dectection.start_resource_detection_task_thread")
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    def test_create_paper_resource_task_accepts_only_paper_files(self, _mock_on_commit, mock_starter):
        paper_file = self.create_file("paper.pdf", "paper")
        image_file = self.create_file("image.png", "image")

        success_response = self.client.post(
            "/api/resource-task/create/",
            {
                "task_type": "paper",
                "task_name": "Paper Task",
                "file_ids": [paper_file.id],
            },
            format="json",
        )
        self.assertEqual(success_response.status_code, 200)
        task = DetectionTask.objects.get(pk=success_response.data["task_id"])
        self.assertEqual(task.task_type, "paper")
        self.assertEqual(task.status, "in_progress")
        self.assertEqual(success_response.data["execution_mode"], "local_async")
        self.assertEqual(list(task.resource_files.values_list("id", flat=True)), [paper_file.id])
        mock_starter.assert_called_once_with("paper", task.id, None)

        failure_response = self.client.post(
            "/api/resource-task/create/",
            {
                "task_type": "paper",
                "task_name": "Bad Paper Task",
                "file_ids": [image_file.id],
            },
            format="json",
        )
        self.assertEqual(failure_response.status_code, 400)
        self.assertEqual(failure_response.data["message"], "paper task only accepts paper resource files")

    @patch("core.views.views_dectection.start_resource_detection_task_thread")
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    def test_create_review_resource_task_requires_both_review_paper_and_linked_review_file(self, _mock_on_commit, mock_starter):
        review_paper = self.create_file("review-paper.pdf", "review_paper")
        unrelated_review_paper = self.create_file("other-paper.pdf", "review_paper")
        linked_review_file = self.create_file("review.txt", "review_file", linked_file=review_paper)
        broken_review_file = self.create_file("broken-review.txt", "review_file", linked_file=unrelated_review_paper)

        success_response = self.client.post(
            "/api/resource-task/create/",
            {
                "task_type": "review",
                "task_name": "Review Task",
                "file_ids": [review_paper.id, linked_review_file.id],
            },
            format="json",
        )
        self.assertEqual(success_response.status_code, 200)
        review_task = DetectionTask.objects.get(pk=success_response.data["task_id"])
        self.assertEqual(review_task.task_type, "review")
        self.assertEqual(review_task.status, "in_progress")
        self.assertEqual(success_response.data["execution_mode"], "local_async")
        self.assertCountEqual(
            list(review_task.resource_files.values_list("id", flat=True)),
            [review_paper.id, linked_review_file.id],
        )
        mock_starter.assert_called_once_with("review", review_task.id, None)

        missing_pair_response = self.client.post(
            "/api/resource-task/create/",
            {
                "task_type": "review",
                "task_name": "Missing Pair",
                "file_ids": [review_paper.id],
            },
            format="json",
        )
        self.assertEqual(missing_pair_response.status_code, 400)
        self.assertEqual(missing_pair_response.data["message"], "review task requires both review_paper and review_file")

        broken_link_response = self.client.post(
            "/api/resource-task/create/",
            {
                "task_type": "review",
                "task_name": "Broken Link",
                "file_ids": [review_paper.id, broken_review_file.id],
            },
            format="json",
        )
        self.assertEqual(broken_link_response.status_code, 400)
        self.assertEqual(broken_link_response.data["message"], "review_file is not correctly linked to review_paper")

    def test_paper_results_endpoint_returns_structured_results(self):
        task = DetectionTask.objects.create(
            organization=self.organization,
            user=self.user,
            task_type="paper",
            task_name="Paper Result Placeholder",
            status="completed",
            text_detection_results={
                "document": {"segment_count": 1},
                "paragraph_results": [{"paragraph_index": 0, "label": "suspicious", "probability": 0.82}],
                "suspicious_paragraphs": [{"paragraph_index": 0, "explanation": "flagged"}],
                "reference_results": [{"reference_index": 0, "exists": True, "is_relevant": True}],
                "image_results": [],
            },
        )

        response = self.client.get(f"/api/paper-results/{task.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["task_id"], task.id)
        self.assertEqual(response.data["status"], "completed")
        self.assertEqual(response.data["results"]["paragraph_results"], task.text_detection_results["paragraph_results"])

    def test_review_task_status_exposes_relevance_results(self):
        review_task = DetectionTask.objects.create(
            organization=self.organization,
            user=self.user,
            task_type="review",
            task_name="Review Closed Loop",
            status="completed",
            text_detection_results={
                "document": {"review_segment_count": 1},
                "paragraph_results": [{"paragraph_index": 0, "label": "clean", "probability": 0.12}],
                "suspicious_paragraphs": [],
                "relevance_results": [
                    {
                        "review_paragraph_index": 0,
                        "paper_paragraph_index": 1,
                        "relevance_score": 0.5,
                        "label": "relevant",
                    }
                ],
            },
        )

        response = self.client.get(f"/api/detection-task/{review_task.id}/status/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["task_type"], "review")
        self.assertEqual(response.data["results"]["relevance_results"][0]["paper_paragraph_index"], 1)
        self.assertIn("1", response.data["result_summary"])

    @patch("core.views.views_dectection.start_resource_detection_task_thread")
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    def test_create_paper_resource_task_uses_local_async_and_accepts_image_options(self, _mock_on_commit, mock_starter):
        paper_file = self.create_file("paper.pdf", "paper")

        response = self.client.post(
            "/api/resource-task/create/",
            {
                "task_type": "paper",
                "task_name": "Paper Async Task",
                "file_ids": [paper_file.id],
                "extract_images": False,
                "if_use_llm": False,
                "method_switches": {
                    "llm": False,
                    "ela": False,
                    "exif": False,
                    "cmd": False,
                    "urn_coarse_v2": False,
                    "urn_blurring": False,
                    "urn_brute_force": False,
                    "urn_contrast": False,
                    "urn_inpainting": False,
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["execution_mode"], "local_async")
        self.assertEqual(response.data["status"], "in_progress")
        task = DetectionTask.objects.get(pk=response.data["task_id"])
        self.assertFalse(task.if_use_llm)
        self.assertEqual(task.method_switches["__paper_extract_images__"], False)
        mock_starter.assert_called_once_with("paper", task.id, None)

    def test_resource_task_creation_defers_paper_start_until_on_commit_and_uses_local_thread(self):
        paper_file = self.create_file("paper.pdf", "paper")
        callbacks = []
        starter_calls = []

        def capture_on_commit(callback):
            callbacks.append(callback)

        def capture_starter(task_type, task_id, api_key):
            starter_calls.append((task_type, task_id, api_key))

        detection_task, _files = create_resource_detection_task(
            user=self.user,
            task_type="paper",
            file_ids=[paper_file.id],
            on_commit=capture_on_commit,
            async_task_starter=capture_starter,
        )

        self.assertEqual(detection_task.status, "in_progress")
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(starter_calls, [])

        callbacks[0]()

        self.assertEqual(starter_calls, [("paper", detection_task.id, None)])

    @patch("core.views.views_dectection.start_resource_detection_task_thread")
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.tasks.run_paper_detection")
    def test_create_paper_resource_task_does_not_call_legacy_task_wrapper(self, mock_run_paper_detection, _mock_on_commit, mock_starter):
        paper_file = self.create_file("paper.pdf", "paper")

        response = self.client.post(
            "/api/resource-task/create/",
            {
                "task_type": "paper",
                "task_name": "Paper Local Thread Only",
                "file_ids": [paper_file.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["execution_mode"], "local_async")
        mock_starter.assert_called_once()
        mock_run_paper_detection.assert_not_called()

    @patch(
        "core.views.views_dectection.start_resource_detection_task_thread",
        side_effect=lambda task_type, task_id, api_key: run_resource_detection_task_async(task_type, task_id, api_key),
    )
    @patch("core.views.views_dectection.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("core.services.integrations.fastdetect_client.requests.post")
    @patch("core.local_detection.get_result", return_value=fake_detection_payload())
    @patch("core.local_detection.fanyi_text", side_effect=lambda text: text)
    def test_paper_report_download_uses_paper_template_for_task_7_fixture(
        self,
        _mock_translate,
        _mock_get_result,
        mock_fastdetect_post,
        _mock_on_commit,
        _mock_starter,
    ):
        self.assertTrue(REPO_TASK_7_REPORT.exists(), "task_7_report.pdf fixture is required for this regression")
        mock_fastdetect_post.return_value = MockFastDetectResponse()

        upload_response = self.client.post(
            "/api/upload/",
            {
                "detection_type": "paper",
                "file": SimpleUploadedFile(
                    "task_7_report.pdf",
                    REPO_TASK_7_REPORT.read_bytes(),
                    content_type="application/pdf",
                ),
            },
            format="multipart",
        )

        self.assertEqual(upload_response.status_code, 200)
        file_id = upload_response.data["file_id"]

        create_response = self.client.post(
            "/api/resource-task/create/",
            {
                "task_type": "paper",
                "task_name": "Paper Fixture Report",
                "file_ids": [file_id],
                "extract_images": True,
                "if_use_llm": False,
                "method_switches": {
                    "llm": False,
                    "ela": False,
                    "exif": True,
                    "cmd": False,
                    "urn_coarse_v2": False,
                    "urn_blurring": False,
                    "urn_brute_force": False,
                    "urn_contrast": False,
                    "urn_inpainting": False,
                },
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 200)
        task = DetectionTask.objects.get(pk=create_response.data["task_id"])
        self.assertEqual(task.task_type, "paper")
        self.assertEqual(task.status, "completed")
        self.assertGreater(task.detection_results.count(), 0)
        self.assertTrue(task.report_file)

        download_response = self.client.get(f"/api/tasks/{task.id}/report/")
        self.assertEqual(download_response.status_code, 200)

        pdf_bytes = b"".join(download_response.streaming_content)
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "".join(page.get_text() for page in pdf[: min(pdf.page_count, 3)])

        self.assertIn("Paper Detection Report", text)
        self.assertIn("task_7_report.pdf", text)
        self.assertNotIn("Image Detection Report", text)
