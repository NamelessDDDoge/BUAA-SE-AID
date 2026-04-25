import os

from django.conf import settings
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from ..models import DetectionResult, PaperDetectionResult, ReviewDetectionResult
from .task_result_store import get_task_results_payload


def build_task_result_summary(task):
    if task.status == "failed":
        return task.error_message or "检测失败"
    if task.status != "completed":
        return "检测进行中"

    if task.task_type == "image":
        counts = task.detection_results.aggregate(
            total=Count("id"),
            fake=Count("id", filter=Q(is_fake=True)),
        )
        total = counts["total"] or 0
        fake = counts["fake"] or 0
        return f"疑似造假 {fake}/{total}"
    if task.task_type == "paper":
        try:
            paper_result = task.paper_detection_result
            suspicious_count = paper_result.paragraph_results.exclude(explanation__isnull=True).exclude(explanation="").count()
        except PaperDetectionResult.DoesNotExist:
            results = get_task_results_payload(task) or {}
            suspicious_count = len(results.get("suspicious_paragraphs", []))
        raw_results = task.text_detection_results or {}
        confirmed_count = len(raw_results.get("confirmed_ai_paragraphs") or [])
        return f"论文检测已完成，疑似段落 {suspicious_count} 段，基本确认AI {confirmed_count} 段"
    if task.task_type == "review":
        raw_results = task.text_detection_results or {}
        review_results = raw_results.get("review_analysis_results") or {}
        overall = review_results.get("overall") or raw_results.get("overall_evaluation") or {}
        template_level = overall.get("template_like_level")
        relevance_level = overall.get("relevance_level")

        if template_level or relevance_level:
            return f"Review 检测已完成，模板化 {template_level or '-'}，相关度 {relevance_level or '-'}"

        try:
            review_result = task.review_detection_result
            relevance_count = review_result.paragraph_results.filter(
                Q(paper_paragraph_index__isnull=False)
                | Q(relevance_score__isnull=False)
                | (Q(relevance_explanation__isnull=False) & ~Q(relevance_explanation=""))
            ).count()
        except ReviewDetectionResult.DoesNotExist:
            results = get_task_results_payload(task) or {}
            relevance_count = len(results.get("relevance_results", []))
        return f"Review 检测已完成，匹配 {relevance_count} 段"
    return "检测已完成"


def serialize_resource_file(file_record):
    stored_path = (file_record.stored_path or "").strip()
    download_url = None
    file_available = False
    download_message = None

    if stored_path.startswith(("http://", "https://")):
        download_url = stored_path
        file_available = True
    elif stored_path:
        abs_path = stored_path if os.path.isabs(stored_path) else os.path.join(settings.MEDIA_ROOT, stored_path)
        download_url = reverse("download_uploaded_resource", kwargs={"file_id": file_record.id})
        file_available = os.path.isfile(abs_path)
        if not file_available:
            download_message = "文件不在当前服务器节点，需同步上传者所在机器的 media/uploads 目录后才能下载。"
    else:
        download_message = "文件路径为空，无法下载。"

    return {
        "file_id": file_record.id,
        "file_name": file_record.file_name,
        "resource_type": file_record.resource_type,
        "file_type": file_record.file_type,
        "file_size": file_record.file_size,
        "linked_file_id": file_record.linked_file_id,
        "stored_path": stored_path,
        "download_url": download_url,
        "file_available": file_available,
        "download_message": download_message,
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
                "image_url": result.image_upload.image.url if result.image_upload.image else None,
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
        "report_file_url": task.report_file.url if task.report_file else None,
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
