import uuid

from django.utils import timezone

from ..event_logger import log_user_event
from ...models import DetectionTask, User


def build_resource_review_placeholder(*, user, task_id, reviewers, reason="", selected_file_ids=None):
    selected_file_ids = selected_file_ids or []
    reason = reason.strip() or "No reason provided"

    if not task_id:
        raise ValueError("task_id is required")
    if not isinstance(reviewers, list) or not reviewers:
        raise ValueError("reviewers is required and must be a non-empty list")
    if selected_file_ids and not isinstance(selected_file_ids, list):
        raise ValueError("selected_file_ids must be a list")

    try:
        detection_task = DetectionTask.objects.get(id=task_id, user=user)
    except DetectionTask.DoesNotExist as exc:
        raise FileNotFoundError("Detection task not found or permission denied") from exc

    if detection_task.task_type not in ("paper", "review"):
        raise ValueError("This endpoint only supports paper/review tasks")
    if detection_task.status != "completed":
        raise ValueError("Task is not completed yet")

    reviewer_users = User.objects.filter(organization=user.organization, id__in=reviewers, role="reviewer")
    if reviewer_users.count() != len(set(reviewers)):
        raise FileNotFoundError("Some reviewer IDs do not exist or are not reviewers")

    task_files = detection_task.resource_files.all()
    if selected_file_ids:
        selected_files = task_files.filter(id__in=selected_file_ids)
        if selected_files.count() != len(set(selected_file_ids)):
            raise ValueError("Some selected_file_ids do not belong to current task")
    else:
        selected_files = task_files

    payload = {
        "placeholder_request_id": f"RR-{uuid.uuid4().hex[:10]}",
        "task_id": detection_task.id,
        "task_type": detection_task.task_type,
        "task_name": detection_task.task_name,
        "reason": reason,
        "reviewers": [{"id": reviewer.id, "username": reviewer.username} for reviewer in reviewer_users],
        "selected_files": [
            {
                "file_id": selected_file.id,
                "file_name": selected_file.file_name,
                "resource_type": selected_file.resource_type,
            }
            for selected_file in selected_files
        ],
        "ai_snapshot": {
            "status": detection_task.status,
            "generated_at": timezone.localtime().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "todo": {
            "persistence": "ReviewRequest/ManualReview resource schema pending",
            "assignment": "admin approval + reviewer assignment pending",
            "report": "resource manual review report pipeline pending",
        },
    }

    log_user_event(
        user=user,
        operation_type="review_request",
        related_model="DetectionTask",
        related_id=detection_task.id,
    )

    return payload
