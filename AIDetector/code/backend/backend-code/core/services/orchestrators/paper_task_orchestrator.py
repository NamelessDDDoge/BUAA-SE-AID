import os
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from ...models import DetectionResult, DetectionTask
from ...utils.report_generator import generate_task_report
from ...utils.task_result_store import store_paper_task_results
from ..capabilities.image_detection_service import run_image_detection_task
from ..capabilities.llm_analysis_service import (
    build_suspicious_paragraph_explanations,
    build_overall_paper_evaluation,
)
from ..capabilities.data_authenticity_service import evaluate_data_authenticity
from ..capabilities.reference_check_service import evaluate_references
from ..capabilities.text_detection_service import analyze_text_segments
from ..resources.document_preprocessor import preprocess_document
from ..resources.document_preprocessor import (
    extract_document_paragraphs,
    extract_document_references,
    split_text_into_segments,
)
from ..resources.text_sanitizer import sanitize_text_content
from ..resources.image_extraction_service import create_image_uploads_for_resource

IMAGE_METHOD_KEYS = {
    "llm",
    "ela",
    "exif",
    "cmd",
    "urn_coarse_v2",
    "urn_blurring",
    "urn_brute_force",
    "urn_contrast",
    "urn_inpainting",
}


def run_paper_detection_task(task_id, api_key=None):
    detection_task = DetectionTask.objects.get(id=task_id)
    detection_task.status = "in_progress"
    detection_task.error_message = ""
    detection_task.save(update_fields=["status", "error_message"])

    file_management = detection_task.resource_files.filter(resource_type="paper").first()
    if not file_management:
        return _mark_task_failed(detection_task, "No paper resource file found")

    file_path = os.path.join(settings.MEDIA_ROOT, file_management.stored_path)
    if not os.path.exists(file_path):
        return _mark_task_failed(detection_task, "Paper file path does not exist")

    processed_document = preprocess_document(file_path)
    override_text = _get_text_override(detection_task)
    if override_text:
        sanitized_text = sanitize_text_content(override_text)
        processed_document = {
            "text_content": sanitized_text,
            "paragraphs": extract_document_paragraphs(sanitized_text),
            "references": extract_document_references(sanitized_text),
            "segments": split_text_into_segments(sanitized_text),
        }
    paragraph_results = analyze_text_segments(processed_document["segments"], api_key=api_key)
    confirmed_ai_paragraphs = [
        {
            "paragraph_index": item.get("paragraph_index"),
            "probability": item.get("probability"),
            "reason": item.get("forgery_reason") or (item.get("details") or {}).get("forgery_reason"),
        }
        for item in paragraph_results
        if bool(item.get("is_ai_confirmed"))
    ]
    explanations = build_suspicious_paragraph_explanations(paragraph_results, api_key=api_key)
    reference_results = evaluate_references(
        text_content=processed_document["text_content"],
        references=processed_document["references"],
    )
    data_authenticity_results = evaluate_data_authenticity(paragraph_results)
    overall_evaluation = build_overall_paper_evaluation(
        paragraph_results=paragraph_results,
        confirmed_ai_paragraphs=confirmed_ai_paragraphs,
        reference_results=reference_results,
        data_authenticity_results=data_authenticity_results,
        api_key=api_key,
    )
    image_results = _run_paper_image_detection(detection_task, file_management)

    results_payload = {
        "document": {
            "file_id": file_management.id,
            "file_name": file_management.file_name,
            "paragraph_count": len(processed_document["paragraphs"]),
            "segment_count": len(processed_document["segments"]),
            "reference_count": len(processed_document["references"]),
            "image_detection_enabled": _paper_image_detection_enabled(detection_task),
        },
        "paragraph_results": paragraph_results,
        "confirmed_ai_paragraphs": confirmed_ai_paragraphs,
        "suspicious_paragraphs": explanations,
        "reference_results": reference_results,
        "data_authenticity_results": data_authenticity_results,
        "overall_evaluation": overall_evaluation,
        "image_results": image_results,
    }

    detection_task.text_detection_results = store_paper_task_results(
        detection_task=detection_task,
        source_file=file_management,
        results_payload=results_payload,
    )
    detection_task.status = "completed"
    detection_task.completion_time = timezone.now()
    detection_task.error_message = ""
    detection_task.save(
        update_fields=["text_detection_results", "status", "completion_time", "error_message"]
    )
    generate_task_report(detection_task)
    return "Paper detection finished"


def _run_paper_image_detection(detection_task, file_management):
    if not _paper_image_detection_enabled(detection_task):
        return []
    if Path(file_management.file_name or "").suffix.lower() not in {".pdf", ".zip"}:
        return []

    image_uploads = create_image_uploads_for_resource(file_management)
    if not image_uploads:
        return []

    run_image_detection_task(detection_task=detection_task, image_uploads=image_uploads)
    image_result_map = {
        result.image_upload_id: result
        for result in DetectionResult.objects.filter(
            detection_task=detection_task,
            image_upload_id__in=[image.id for image in image_uploads],
        ).select_related("image_upload")
    }
    return [
        {
            "image_id": image.id,
            "page_number": image.page_number,
            "status": image_result_map[image.id].status if image.id in image_result_map else "pending",
            "is_fake": image_result_map[image.id].is_fake if image.id in image_result_map else None,
            "confidence_score": (
                image_result_map[image.id].confidence_score if image.id in image_result_map else None
            ),
        }
        for image in image_uploads
    ]


def _paper_image_detection_enabled(detection_task):
    method_switches = detection_task.method_switches or {}
    if "__paper_extract_images__" in method_switches:
        return bool(method_switches["__paper_extract_images__"]) and any(
            bool(method_switches.get(method_name))
            for method_name in IMAGE_METHOD_KEYS
        )
    return True


def _mark_task_failed(detection_task, message):
    detection_task.status = "failed"
    detection_task.error_message = message
    detection_task.completion_time = timezone.now()
    detection_task.save(update_fields=["status", "error_message", "completion_time"])
    return message


def _get_text_override(detection_task):
    raw_payload = detection_task.text_detection_results
    if not isinstance(raw_payload, dict):
        return ""
    text_override = raw_payload.get("text_override")
    if isinstance(text_override, str):
        return text_override
    return ""
