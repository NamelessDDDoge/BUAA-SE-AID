from unittest.mock import patch

from django.test import TestCase

from core.models import DetectionTask, Organization, User
from core.services.orchestrators import resource_task_orchestrator


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
