from django.utils import timezone

from ..event_logger import log_user_event
from ...models import DetectionTask, FileManagement


def create_resource_detection_task(*, user, task_type, file_ids, task_name="", api_key=None, paper_scheduler=None):
    if task_type not in {"paper", "review"}:
        raise ValueError("task_type must be paper or review")

    if not isinstance(file_ids, list) or not file_ids:
        raise ValueError("file_ids is required and must be a non-empty list")

    if not task_name:
        timestamp = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
        task_name = f"论文检测 {timestamp}" if task_type == "paper" else f"Review检测 {timestamp}"

    files = FileManagement.objects.filter(id__in=file_ids, user=user)
    if files.count() != len(set(file_ids)):
        raise FileNotFoundError("Some files do not exist or do not belong to current user")

    file_list = list(files)
    resource_types = {f.resource_type for f in file_list}

    if task_type == "paper":
        if resource_types != {"paper"}:
            raise ValueError("paper task only accepts paper resource files")
    else:
        if not ({"review_paper", "review_file"} <= resource_types):
            raise ValueError("review task requires both review_paper and review_file")

        review_paper_ids = {f.id for f in file_list if f.resource_type == "review_paper"}
        review_files = [f for f in file_list if f.resource_type == "review_file"]
        if not any(rv.linked_file and rv.linked_file.id in review_paper_ids for rv in review_files):
            raise ValueError("review_file is not correctly linked to review_paper")

    detection_task = DetectionTask.objects.create(
        organization=user.organization,
        user=user,
        task_type=task_type,
        task_name=task_name,
        status="pending",
    )
    detection_task.resource_files.add(*file_list)

    log_user_event(
        user=user,
        operation_type="detection",
        related_model="DetectionTask",
        related_id=detection_task.id,
    )

    if task_type == "paper" and paper_scheduler is not None:
        paper_scheduler(detection_task.id, api_key)

    return detection_task, file_list
