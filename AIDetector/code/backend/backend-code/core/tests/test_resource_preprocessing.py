import shutil
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import DetectionTask, FileManagement, Organization, User
from core.tasks import run_paper_detection


@override_settings(ENABLE_FANYI=False)
class ResourcePreprocessingTests(TestCase):
    def setUp(self):
        temp_root = Path.home() / ".codex" / "memories" / "buaa-se-aid-resource-preprocess-tests"
        shutil.rmtree(temp_root, ignore_errors=True)
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_media = temp_root
        self.override = override_settings(MEDIA_ROOT=str(temp_root))
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.temp_media, ignore_errors=True))

        self.organization = Organization.objects.create(name="Preprocess Org", email="preprocess-org@example.com")
        self.user = User.objects.create_user(
            username="preprocess-user",
            email="preprocess-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )

    def create_text_file(self, file_name, content):
        uploads_dir = self.temp_media / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        file_path = uploads_dir / file_name
        file_path.write_text(content, encoding="utf-8")
        return FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name=file_name,
            file_size=file_path.stat().st_size,
            file_type="text/plain",
            resource_type="paper",
            stored_path=f"uploads/{file_name}",
        )

    @patch("core.services.orchestrators.paper_task_orchestrator.run_image_detection_task")
    @patch("core.services.integrations.fastdetect_client.requests.post")
    def test_run_paper_detection_splits_text_into_500_char_segments(self, mock_post, mock_image_detection):
        mock_post.return_value.json.return_value = {"data": {"prob": 0.65, "details": {"source": "mock"}}}
        mock_post.return_value.raise_for_status.return_value = None
        file_record = self.create_text_file(
            "paper.txt",
            "\n".join(
                [
                    "A" * 300,
                    "B" * 300,
                    "C" * 300,
                ]
            ),
        )
        task = DetectionTask.objects.create(
            user=self.user,
            organization=self.organization,
            task_type="paper",
            task_name="Segmented Paper",
            status="pending",
        )
        task.resource_files.add(file_record)

        result = run_paper_detection(task.id)

        task.refresh_from_db()
        self.assertEqual(result, "Paper detection finished")
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.text_detection_results["document"]["segment_count"], 3)
        self.assertEqual(len(task.text_detection_results["paragraph_results"]), 3)
        self.assertEqual(len(task.text_detection_results["suspicious_paragraphs"]), 3)
        self.assertEqual(task.completion_time is not None, True)
        self.assertEqual(mock_post.call_count, 3)
        self.assertTrue(all(item["text"] for item in task.text_detection_results["paragraph_results"]))
        mock_image_detection.assert_not_called()

    @patch("core.services.orchestrators.paper_task_orchestrator.run_image_detection_task")
    @patch("core.services.integrations.fastdetect_client.requests.post")
    def test_run_paper_detection_handles_missing_decodable_text(self, mock_post, mock_image_detection):
        mock_post.return_value.json.return_value = {"data": {"prob": 0.1, "details": {}}}
        mock_post.return_value.raise_for_status.return_value = None
        uploads_dir = self.temp_media / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        file_path = uploads_dir / "paper.bin"
        file_path.write_bytes(b"\xff\xfe\x00\xff")
        file_record = FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name="paper.bin",
            file_size=file_path.stat().st_size,
            file_type="application/octet-stream",
            resource_type="paper",
            stored_path="uploads/paper.bin",
        )
        task = DetectionTask.objects.create(
            user=self.user,
            organization=self.organization,
            task_type="paper",
            task_name="Unreadable Paper",
            status="pending",
        )
        task.resource_files.add(file_record)

        run_paper_detection(task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, "completed")
        self.assertEqual(len(task.text_detection_results["paragraph_results"]), 1)
        self.assertTrue(task.text_detection_results["paragraph_results"][0]["text"])
        self.assertEqual(task.text_detection_results["reference_results"], [])
        mock_image_detection.assert_not_called()
