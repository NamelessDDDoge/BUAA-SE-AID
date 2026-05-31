from unittest.mock import patch

from django.test import TestCase

from core.models import DetectionTask, Organization, User
from core.services.orchestrators import resource_task_orchestrator
from core.models import FileManagement


class ResourceTaskExecutorTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Resource Executor Org", email="resource-executor@example.com")
        self.user = User.objects.create_user(
            username="resource-executor-user",
            email="resource-executor-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )

    @patch.object(resource_task_orchestrator.RESOURCE_TASK_EXECUTOR, "submit")
    @patch.object(resource_task_orchestrator.LLM_RESOURCE_TASK_EXECUTOR, "submit")
    def test_non_llm_resource_task_uses_normal_executor(self, mock_llm_submit, mock_normal_submit):
        task = DetectionTask.objects.create(
            organization=self.organization,
            user=self.user,
            task_type="paper",
            task_name="Normal Resource Task",
            status="in_progress",
            if_use_llm=False,
        )

        future = resource_task_orchestrator.start_resource_detection_task_thread("paper", task.id, None)

        self.assertEqual(future, mock_normal_submit.return_value)
        mock_normal_submit.assert_called_once_with(
            resource_task_orchestrator.run_resource_detection_task_async,
            "paper",
            task.id,
            None,
        )
        mock_llm_submit.assert_not_called()

    @patch.object(resource_task_orchestrator.RESOURCE_TASK_EXECUTOR, "submit")
    @patch.object(resource_task_orchestrator.LLM_RESOURCE_TASK_EXECUTOR, "submit")
    def test_llm_resource_task_uses_llm_executor(self, mock_llm_submit, mock_normal_submit):
        task = DetectionTask.objects.create(
            organization=self.organization,
            user=self.user,
            task_type="review",
            task_name="LLM Resource Task",
            status="in_progress",
            if_use_llm=True,
        )

        future = resource_task_orchestrator.start_resource_detection_task_thread("review", task.id, "demo-key")

        self.assertEqual(future, mock_llm_submit.return_value)
        mock_llm_submit.assert_called_once_with(
            resource_task_orchestrator.run_resource_detection_task_async,
            "review",
            task.id,
            "demo-key",
        )
        mock_normal_submit.assert_not_called()


class ResourceTaskSplitTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Resource Split Org", email="resource-split@example.com")
        self.user = User.objects.create_user(
            username="resource-split-user",
            email="resource-split-user@example.com",
            password="pass123456",
            role="publisher",
            organization=self.organization,
        )

    def create_file(self, file_name, resource_type, linked_file=None):
        return FileManagement.objects.create(
            user=self.user,
            organization=self.organization,
            file_name=file_name,
            file_size=128,
            file_type="text/plain",
            resource_type=resource_type,
            stored_path=f"uploads/{file_name}",
            linked_file=linked_file,
        )

    @patch("core.services.orchestrators.resource_task_orchestrator.run_paper_detection_task")
    def test_run_paper_resource_task_marks_task_in_progress_when_worker_starts(self, mock_runner):
        paper = self.create_file("paper.txt", "paper")
        task, _files = resource_task_orchestrator.create_resource_detection_task(
            user=self.user,
            task_type="paper",
            file_ids=[paper.id],
            async_task_starter=lambda *args, **kwargs: None,
            on_commit=lambda fn: None,
        )

        resource_task_orchestrator.run_resource_detection_task_async("paper", task.id, api_key=None)

        task.refresh_from_db()
        self.assertEqual(task.status, "in_progress")
        mock_runner.assert_called_once_with(task.id, api_key=None)

    @patch("core.services.orchestrators.resource_task_orchestrator.run_review_detection_task")
    def test_run_review_resource_task_marks_task_in_progress_when_worker_starts(self, mock_runner):
        paper = self.create_file("paper.txt", "review_paper")
        review = self.create_file("review.txt", "review_file", linked_file=paper)
        task, _files = resource_task_orchestrator.create_resource_detection_task(
            user=self.user,
            task_type="review",
            file_ids=[paper.id, review.id],
            async_task_starter=lambda *args, **kwargs: None,
            on_commit=lambda fn: None,
        )

        resource_task_orchestrator.run_resource_detection_task_async("review", task.id, api_key="demo")

        task.refresh_from_db()
        self.assertEqual(task.status, "in_progress")
        mock_runner.assert_called_once_with(task.id, api_key="demo")

    def test_create_resource_detection_tasks_splits_multiple_papers_into_individual_tasks(self):
        paper_a = self.create_file("paper-a.txt", "paper")
        paper_b = self.create_file("paper-b.txt", "paper")

        tasks, file_groups = resource_task_orchestrator.create_resource_detection_tasks(
            user=self.user,
            task_type="paper",
            file_ids=[paper_a.id, paper_b.id],
        )

        self.assertEqual(len(tasks), 2)
        self.assertEqual(len(file_groups), 2)
        self.assertEqual([group[0].id for group in file_groups], [paper_a.id, paper_b.id])
        self.assertEqual(tasks[0].resource_files.count(), 1)
        self.assertEqual(tasks[1].resource_files.count(), 1)
        self.assertTrue(all(task.status == "pending" for task in tasks))

    def test_create_resource_detection_tasks_rejects_text_override_for_multiple_papers(self):
        paper_a = self.create_file("paper-a.txt", "paper")
        paper_b = self.create_file("paper-b.txt", "paper")

        with self.assertRaises(ValueError):
            resource_task_orchestrator.create_resource_detection_tasks(
                user=self.user,
                task_type="paper",
                file_ids=[paper_a.id, paper_b.id],
                text_override="edited text for one paper",
            )

        self.assertEqual(DetectionTask.objects.filter(user=self.user, task_type="paper").count(), 0)

    def test_create_resource_detection_tasks_splits_one_paper_and_multiple_reviews(self):
        paper = self.create_file("paper.txt", "review_paper")
        review_a = self.create_file("review-a.txt", "review_file", linked_file=paper)
        review_b = self.create_file("review-b.txt", "review_file", linked_file=paper)

        tasks, file_groups = resource_task_orchestrator.create_resource_detection_tasks(
            user=self.user,
            task_type="review",
            file_ids=[paper.id, review_a.id, review_b.id],
        )

        self.assertEqual(len(tasks), 2)
        self.assertEqual(len(file_groups), 2)
        self.assertEqual(file_groups[0][0].id, paper.id)
        self.assertEqual(file_groups[1][0].id, paper.id)
        self.assertEqual(file_groups[0][1].id, review_a.id)
        self.assertEqual(file_groups[1][1].id, review_b.id)
        self.assertEqual(tasks[0].resource_files.count(), 2)
        self.assertEqual(tasks[1].resource_files.count(), 2)
        self.assertTrue(all(task.status == "pending" for task in tasks))

    def test_create_resource_detection_tasks_rejects_review_text_override_for_multiple_reviews(self):
        paper = self.create_file("paper.txt", "review_paper")
        review_a = self.create_file("review-a.txt", "review_file", linked_file=paper)
        review_b = self.create_file("review-b.txt", "review_file", linked_file=paper)

        with self.assertRaises(ValueError):
            resource_task_orchestrator.create_resource_detection_tasks(
                user=self.user,
                task_type="review",
                file_ids=[paper.id, review_a.id, review_b.id],
                review_text_override="edited review",
            )

        self.assertEqual(DetectionTask.objects.filter(user=self.user, task_type="review").count(), 0)

    def test_create_resource_detection_tasks_shares_paper_override_for_multiple_reviews(self):
        paper = self.create_file("paper.txt", "review_paper")
        review_a = self.create_file("review-a.txt", "review_file", linked_file=paper)
        review_b = self.create_file("review-b.txt", "review_file", linked_file=paper)

        tasks, _file_groups = resource_task_orchestrator.create_resource_detection_tasks(
            user=self.user,
            task_type="review",
            file_ids=[paper.id, review_a.id, review_b.id],
            paper_text_override="edited shared paper",
        )

        self.assertEqual(len(tasks), 2)
        self.assertTrue(all(
            task.text_detection_results["paper_text_override"] == "edited shared paper"
            for task in tasks
        ))
