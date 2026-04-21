import shutil
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import DetectionTask, FileManagement, Organization, User


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

    @patch("core.tasks.run_paper_detection.delay")
    def test_create_paper_resource_task_accepts_only_paper_files(self, mock_delay):
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
        self.assertEqual(list(task.resource_files.values_list("id", flat=True)), [paper_file.id])
        mock_delay.assert_called_once_with(task.id, None)

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

    def test_create_review_resource_task_requires_both_review_paper_and_linked_review_file(self):
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
        self.assertCountEqual(
            list(review_task.resource_files.values_list("id", flat=True)),
            [review_paper.id, linked_review_file.id],
        )

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

    def test_paper_results_endpoint_returns_placeholder_json_results(self):
        task = DetectionTask.objects.create(
            organization=self.organization,
            user=self.user,
            task_type="paper",
            task_name="Paper Result Placeholder",
            status="completed",
            text_detection_results=[
                {"paragraph_index": 0, "label": "suspicious", "score": 0.82},
            ],
        )

        response = self.client.get(f"/api/paper-results/{task.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["task_id"], task.id)
        self.assertEqual(response.data["status"], "completed")
        self.assertEqual(response.data["results"], task.text_detection_results)
