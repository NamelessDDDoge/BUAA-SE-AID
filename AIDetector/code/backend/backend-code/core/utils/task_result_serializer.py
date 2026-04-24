from django.utils import timezone

from ..models import DetectionResult
from .task_result_store import get_task_results_payload


def build_task_result_summary(task):
    if task.status == "failed":
        return task.error_message or "检测失败"
    if task.status != "completed":
        return "检测进行中"

    if task.task_type == "image":
        total = task.detection_results.count()
        fake = task.detection_results.filter(is_fake=True).count()
        return f"疑似造假 {fake}/{total}"
    if task.task_type == "paper":
        results = get_task_results_payload(task) or {}
        suspicious_count = len(results.get("suspicious_paragraphs", []))
        confirmed_count = len(results.get("confirmed_ai_paragraphs", []))
        return f"论文检测已完成，疑似段落 {suspicious_count} 段，基本确认AI {confirmed_count} 段"
    if task.task_type == "review":
        results = get_task_results_payload(task) or {}
        review_results = results.get("review_analysis_results") or {}
        overall = review_results.get("overall") or {}
        template_level = overall.get("template_like_level", "low")
        relevance_level = overall.get("relevance_level", "low")
        return f"Review 检测已完成，模板化 {template_level}，相关度 {relevance_level}"
    return "检测已完成"


def serialize_resource_file(file_record):
    return {
        "file_id": file_record.id,
        "file_name": file_record.file_name,
        "resource_type": file_record.resource_type,
        "file_type": file_record.file_type,
        "file_size": file_record.file_size,
        "upload_time": timezone.localtime(file_record.upload_time),
    }


def build_task_progress(task):
    detection_results = task.detection_results.all()
    return {
        "total_results": detection_results.count(),
        "completed_results": detection_results.filter(status="completed").count(),
        "pending_results": detection_results.filter(status="in_progress").count(),
        "failed_results": detection_results.filter(status="failed").count(),
    }


def build_task_results(task):
    if task.task_type == "image":
        detection_results = (
            DetectionResult.objects.filter(detection_task=task)
            .select_related("image_upload")
            .order_by("id")
        )
        image_results = [
            {
                "result_id": result.id,
                "image_id": result.image_upload_id,
                "file_id": result.image_upload.file_management_id,
                "page_number": result.image_upload.page_number,
                "status": result.status,
                "is_fake": result.is_fake,
                "confidence_score": result.confidence_score,
                "detection_time": timezone.localtime(result.detection_time) if result.detection_time else None,
            }
            for result in detection_results
        ]
        return {
            "result_type": "image",
            "summary": {
                "total_images": len(image_results),
                "fake_images": sum(1 for item in image_results if item["is_fake"] is True),
                "completed_images": sum(1 for item in image_results if item["status"] == "completed"),
            },
            "image_results": image_results,
        }

    task_results = get_task_results_payload(task) or {}
    task_results["result_type"] = task.task_type
    return task_results


def build_detection_task_status_payload(task):
    resource_files = list(task.resource_files.all().order_by("id"))
    results = build_task_results(task)

    payload = {
        "task_id": task.id,
        "task_name": task.task_name,
        "task_type": task.task_type,
        "status": task.status,
        "upload_time": timezone.localtime(task.upload_time),
        "completion_time": timezone.localtime(task.completion_time) if task.completion_time else None,
        "result_summary": build_task_result_summary(task),
        "error_message": task.error_message,
        "is_running": task.status in {"pending", "in_progress"},
        "progress": build_task_progress(task),
        "resource_files": [serialize_resource_file(file_record) for file_record in resource_files],
        "results": results,
    }

    if task.task_type == "image":
        payload["detection_results"] = results["image_results"]
        payload["fake_resource_files"] = []
        payload["normal_resource_files"] = []
        payload["pending_resource_files"] = []
        payload["resource_split_note"] = None
    elif task.task_type == "paper":
        payload["detection_results"] = results.get("image_results", [])
        payload["fake_resource_files"] = []
        payload["normal_resource_files"] = payload["resource_files"]
        payload["pending_resource_files"] = []
        payload["resource_split_note"] = (
            "Paper detection currently does not expose fake/normal grouping."
            if task.status == "completed"
            else None
        )
    else:
        payload["detection_results"] = []
        payload["fake_resource_files"] = []
        payload["normal_resource_files"] = payload["resource_files"] if task.status == "completed" else []
        payload["pending_resource_files"] = payload["resource_files"] if task.status != "completed" else []
        payload["resource_split_note"] = (
            "Review tasks do not expose fake/normal grouping; use results.relevance_results instead."
            if task.status == "completed"
            else None
        )

    return payload
