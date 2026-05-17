import shutil
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from core.services.capabilities.image import local_inference_client
from core.services.orchestrators import image_task_orchestrator
from core.models import DetectionTask, FileManagement, ImageUpload, Organization, User


@override_settings(ENABLE_FANYI=False)
class LocalInferenceIsolationTests(TestCase):
    def setUp(self):
        temp_root = Path.home() / ".codex" / "memories" / "buaa-se-aid-concurrency-tests"
        shutil.rmtree(temp_root, ignore_errors=True)
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_root = temp_root
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

    @patch("core.services.capabilities.image.local_inference_client._run_local_inference", return_value=[("llm", [])])
    def test_get_result_creates_distinct_request_dirs_for_separate_calls(self, mock_run_local_inference):
        zip_path = self.temp_root / "input.zip"
        json_path = self.temp_root / "input.json"
        zip_path.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
        json_path.write_text('{"cmd_block_size": 64}', encoding="utf-8")

        shared_root = self.temp_root / "shared"
        shared_root.mkdir(parents=True, exist_ok=True)

        with patch.object(local_inference_client, "AI_SERVICE_TEST_DIR", shared_root):
            local_inference_client.get_result(zip_path, json_path)
            local_inference_client.get_result(zip_path, json_path)

        first_request_dir = Path(mock_run_local_inference.call_args_list[0].kwargs["request_dir"])
        second_request_dir = Path(mock_run_local_inference.call_args_list[1].kwargs["request_dir"])

        self.assertNotEqual(first_request_dir, second_request_dir)
        self.assertEqual(first_request_dir.parent, shared_root)
        self.assertEqual(second_request_dir.parent, shared_root)
        self.assertFalse(first_request_dir.exists())
        self.assertFalse(second_request_dir.exists())


class ImageTaskExecutorIsolationTests(TestCase):
    @patch.object(image_task_orchestrator.IMAGE_TASK_EXECUTOR, "submit")
    @patch.object(image_task_orchestrator.LLM_IMAGE_TASK_EXECUTOR, "submit")
    def test_llm_and_non_llm_tasks_use_different_executors(self, mock_llm_submit, mock_normal_submit):
        def fake_runner(*args, **kwargs):
            return None

        normal_future = image_task_orchestrator.start_image_detection_task_thread(
            1,
            [100],
            False,
            1,
            task_runner=fake_runner,
        )
        llm_future = image_task_orchestrator.start_image_detection_task_thread(
            2,
            [200],
            True,
            1,
            task_runner=fake_runner,
        )

        self.assertEqual(normal_future, mock_normal_submit.return_value)
        self.assertEqual(llm_future, mock_llm_submit.return_value)
        mock_normal_submit.assert_called_once_with(fake_runner, 1, [100], False, 1)
        mock_llm_submit.assert_called_once_with(fake_runner, 2, [200], True, 1)


class ImageTaskSplitTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Image Split Org", email="image-split@example.com")
        self.user = User.objects.create_user(
            username="image-split-user",
            email="image-split-user@example.com",
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
        self.image_upload_1 = ImageUpload.objects.create(file_management=self.file_record, image="extracted_images/a.png")
        self.image_upload_2 = ImageUpload.objects.create(file_management=self.file_record, image="extracted_images/b.png")

    def test_create_image_detection_tasks_splits_each_image_into_individual_task(self):
        tasks, image_groups = image_task_orchestrator.create_image_detection_tasks(
            user=self.user,
            image_ids=[self.image_upload_1.id, self.image_upload_2.id],
            on_commit=lambda fn: fn(),
            async_task_starter=lambda *args, **kwargs: None,
        )

        self.assertEqual(len(tasks), 2)
        self.assertEqual(len(image_groups), 2)
        self.assertEqual(image_groups[0][0].id, self.image_upload_1.id)
        self.assertEqual(image_groups[1][0].id, self.image_upload_2.id)
        self.assertTrue(all(task.resource_files.count() == 1 for task in tasks))
        self.assertTrue(all(task.detection_results.count() == 1 for task in tasks))
