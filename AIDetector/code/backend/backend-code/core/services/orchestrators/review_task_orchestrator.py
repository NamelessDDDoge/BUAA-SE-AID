import uuid
import os

from django.conf import settings
from django.utils import timezone

from ..event_logger import log_user_event
from ...models import DetectionTask, User
from ...utils.report_generator import generate_task_report
from ...utils.task_result_store import store_review_task_results
from ..capabilities.review_analysis_service import build_review_qualification, evaluate_review_analysis
from ..capabilities.review_relevance_service import analyze_review_relevance
from ..resources.document_preprocessor import preprocess_document
from ..resources.document_preprocessor import (
    extract_document_paragraphs,
    extract_document_references,
    split_text_into_segments,
    parse_document_sections,
)
from ..resources.text_sanitizer import sanitize_text_content


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
    paper_override_text = _get_text_override(detection_task, "paper_text_override")
    review_override_text = _get_text_override(detection_task, "review_text_override")
    legacy_review_override_text = _get_text_override(detection_task, "text_override")

    if paper_override_text:
        paper_document = _build_document_from_text(sanitize_text_content(paper_override_text))
    if review_override_text:
        review_document = _build_document_from_text(sanitize_text_content(review_override_text))
    elif legacy_review_override_text:
        review_document = _build_document_from_text(sanitize_text_content(legacy_review_override_text))

    analysis_results = evaluate_review_analysis(
        paper_document=paper_document,
        review_document=review_document,
        api_key=api_key,
        llm_model_name=detection_task.llm_model_name,
    )
    local_relevance_results = analyze_review_relevance(
        review_segments=review_document.get("paragraphs") or [],
        paper_segments=paper_document.get("paragraphs") or [],
    )
    analysis_results["paragraph_results"] = _merge_review_analysis_with_relevance(
        analysis_results.get("paragraph_results", []),
        local_relevance_results,
    )
    if analysis_results.get("overall", {}).get("qualification_label") != "unavailable":
        overall = analysis_results.get("overall") or {}
        analysis_results["overall"] = {
            **overall,
            **build_review_qualification(overall, analysis_results.get("paragraph_results", [])),
        }
    paragraph_results = []
    analysis_map = {
        item.get("review_paragraph_index"): item
        for item in analysis_results.get("paragraph_results", [])
        if item.get("review_paragraph_index") is not None
    }
    for index, paragraph in enumerate(review_document.get("paragraphs") or []):
        analysis_item = analysis_map.get(index, {})
        template_level = analysis_item.get("template_like_level", "low")
        wrongness_level = analysis_item.get("wrongness_level", "low")
        relevance_score = _coerce_optional_float(analysis_item.get("relevance_score"))
        relevance_level = analysis_item.get("relevance_level", "")
        if analysis_results.get("overall", {}).get("qualification_label") == "unavailable":
            probability = 0.0
            label = "unavailable"
        else:
            probability = _build_review_paragraph_risk(
                template_level=template_level,
                wrongness_level=wrongness_level,
                relevance_level=relevance_level,
                relevance_score=relevance_score,
            )
            label = (
                "suspicious"
                if template_level == "high"
                or wrongness_level == "high"
                or _normalize_relevance_level(relevance_level) == "low"
                or (relevance_score is not None and relevance_score < 0.45)
                else "clean"
            )
        paragraph_results.append(
            {
                "paragraph_index": index,
                "text": paragraph,
                "probability": probability,
                "label": label,
                "details": {
                    **analysis_item,
                    "template_like_level": template_level,
                    "wrongness_level": wrongness_level,
                    "relevance_score": relevance_score,
                    "relevance_level": relevance_level,
                },
            }
        )

    suspicious_paragraphs = [
        {
            "paragraph_index": item["paragraph_index"],
            "probability": item["probability"],
            "explanation": item.get("details", {}).get("explanation") or item.get("text", ""),
        }
        for item in paragraph_results
        if item.get("label") == "suspicious"
    ]

    detection_task.text_detection_results = store_review_task_results(
        detection_task=detection_task,
        paper_file=paper_file,
        review_file=review_file,
        results_payload={
            "document": {
                "paper_file_id": paper_file.id,
                "paper_file_name": paper_file.file_name,
                "review_file_id": review_file.id,
                "review_file_name": review_file.file_name,
                "paper_segment_count": len(paper_document["segments"]),
                "review_segment_count": len(review_document["segments"]),
                "paper_paragraph_count": len(paper_document["paragraphs"]),
                "review_paragraph_count": len(review_document["paragraphs"]),
            },
            "paragraph_results": paragraph_results,
            "suspicious_paragraphs": suspicious_paragraphs,
            "review_analysis_results": analysis_results,
            "relevance_results": analysis_results.get("paragraph_results", []),
        },
    )
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


def _build_document_from_text(text_content):
    sections = parse_document_sections(text_content)
    core_text = sections.get("abstract", "") + "\n\n" + sections.get("body", "")
    if not core_text.strip():
        core_text = text_content
        
    return {
        "text_content": text_content,
        "paragraphs": extract_document_paragraphs(text_content),
        "sections": sections,
        "references": extract_document_references(text_content),
        "segments": split_text_into_segments(core_text),
    }


def _get_text_override(detection_task, key="text_override"):
    raw_payload = detection_task.text_detection_results
    if not isinstance(raw_payload, dict):
        return ""
    text_override = raw_payload.get(key)
    return text_override if isinstance(text_override, str) else ""


def _build_review_paragraph_risk(*, template_level, wrongness_level, relevance_level, relevance_score):
    template_risk = _risk_from_bad_level(template_level)
    wrongness_risk = _risk_from_bad_level(wrongness_level)
    relevance_risk = _risk_from_relevance(relevance_level, relevance_score)
    return max(template_risk, wrongness_risk, relevance_risk)


def _risk_from_bad_level(level):
    normalized = str(level or "").strip().lower()
    if normalized == "high":
        return 0.85
    if normalized == "medium":
        return 0.55
    return 0.15


def _risk_from_relevance(level, score):
    normalized = _normalize_relevance_level(level)
    level_risk = {
        "high": 0.15,
        "medium": 0.55,
        "low": 0.85,
    }.get(normalized, 0.35)
    if score is None:
        return level_risk
    return max(level_risk, 1 - max(0.0, min(1.0, score)))


def _normalize_relevance_level(level):
    normalized = str(level or "").strip().lower()
    if normalized in {"high", "relevant"}:
        return "high"
    if normalized == "medium":
        return "medium"
    if normalized in {"low", "weak_match"}:
        return "low"
    return "unknown"


def _coerce_optional_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _merge_review_analysis_with_relevance(analysis_results, relevance_results):
    analysis_results = analysis_results if isinstance(analysis_results, list) else []
    relevance_results = relevance_results if isinstance(relevance_results, list) else []
    analysis_map = {
        item.get("review_paragraph_index"): item
        for item in analysis_results
        if isinstance(item, dict) and item.get("review_paragraph_index") is not None
    }
    relevance_map = {
        item.get("review_paragraph_index"): item
        for item in relevance_results
        if isinstance(item, dict) and item.get("review_paragraph_index") is not None
    }
    merged_results = []
    for review_index in sorted(set(analysis_map.keys()) | set(relevance_map.keys())):
        analysis_item = analysis_map.get(review_index) or {}
        relevance_item = relevance_map.get(review_index) or {}
        merged_results.append(
            {
                **relevance_item,
                **analysis_item,
                "review_paragraph_index": review_index,
                "review_text": analysis_item.get("review_text") or relevance_item.get("review_text"),
                "paper_paragraph_index": relevance_item.get("paper_paragraph_index"),
                "paper_text": relevance_item.get("paper_text", ""),
                "relevance_score": (
                    analysis_item.get("relevance_score")
                    if analysis_item.get("relevance_score") is not None
                    else relevance_item.get("relevance_score")
                ),
                "relevance_level": (
                    analysis_item.get("relevance_level")
                    or _relevance_level_from_label(relevance_item.get("label"))
                ),
                "local_relevance_score": relevance_item.get("relevance_score"),
                "local_relevance_label": relevance_item.get("label"),
                "local_relevance_explanation": relevance_item.get("explanation"),
            }
        )
    return merged_results


def _relevance_level_from_label(label):
    normalized = str(label or "").strip().lower()
    if normalized == "relevant":
        return "high"
    if normalized == "weak_match":
        return "low"
    return ""
