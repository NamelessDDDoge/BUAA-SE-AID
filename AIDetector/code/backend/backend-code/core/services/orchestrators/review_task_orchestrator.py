import uuid
import os

from django.conf import settings
from django.utils import timezone

from ..event_logger import log_user_event
from ...models import DetectionTask, User
from ...utils.report_generator import generate_task_report
from ..capabilities.llm_analysis_service import build_suspicious_paragraph_explanations
from ..capabilities.review_relevance_service import analyze_review_relevance
from ..capabilities.text_detection_service import analyze_text_segments
from ..resources.document_preprocessor import preprocess_document
from ..resources.text_sanitizer import sanitize_json_like


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


def run_review_detection_task(task_id, api_key=None):
    detection_task = DetectionTask.objects.get(id=task_id)
    detection_task.status = "in_progress"
    detection_task.error_message = ""
    detection_task.save(update_fields=["status", "error_message"])

    paper_file = detection_task.resource_files.filter(resource_type="review_paper").first()
    review_file = detection_task.resource_files.filter(resource_type="review_file").first()
    if not paper_file or not review_file:
        return _mark_review_task_failed(detection_task, "Review task requires both review_paper and review_file")

    paper_path = os.path.join(settings.MEDIA_ROOT, paper_file.stored_path)
    review_path = os.path.join(settings.MEDIA_ROOT, review_file.stored_path)
    if not os.path.exists(paper_path) or not os.path.exists(review_path):
        return _mark_review_task_failed(detection_task, "Review task file path does not exist")

    paper_document = preprocess_document(paper_path)
    review_document = preprocess_document(review_path)
    paragraph_results = analyze_text_segments(review_document["segments"], api_key=api_key)
    suspicious_paragraphs = build_suspicious_paragraph_explanations(paragraph_results, api_key=api_key)
    relevance_results = analyze_review_relevance(
        review_segments=review_document["segments"],
        paper_segments=paper_document["segments"],
    )

    detection_task.text_detection_results = sanitize_json_like({
        "document": {
            "paper_file_id": paper_file.id,
            "paper_file_name": paper_file.file_name,
            "review_file_id": review_file.id,
            "review_file_name": review_file.file_name,
            "paper_segment_count": len(paper_document["segments"]),
            "review_segment_count": len(review_document["segments"]),
        },
        "paragraph_results": paragraph_results,
        "suspicious_paragraphs": suspicious_paragraphs,
        "relevance_results": relevance_results,
    })
    detection_task.status = "completed"
    detection_task.completion_time = timezone.now()
    detection_task.error_message = ""
    detection_task.save(
        update_fields=["text_detection_results", "status", "completion_time", "error_message"]
    )
    generate_task_report(detection_task)
    return "Review detection finished"


def _mark_review_task_failed(detection_task, message):
    detection_task.status = "failed"
    detection_task.error_message = message
    detection_task.completion_time = timezone.now()
    detection_task.save(update_fields=["status", "error_message", "completion_time"])
    return message
