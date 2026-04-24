from ..models import (
    DetectionResult,
    PaperDetectionResult,
    PaperParagraphResult,
    PaperReferenceResult,
    ReviewDetectionResult,
    ReviewParagraphResult,
)
from ..services.resources.text_sanitizer import sanitize_json_like


def store_paper_task_results(*, detection_task, source_file, results_payload):
    sanitized_payload = sanitize_json_like(results_payload)
    document = sanitized_payload.get("document", {})
    paragraph_results = sanitized_payload.get("paragraph_results", [])
    explanation_map = {
        item.get("paragraph_index"): item.get("explanation")
        for item in sanitized_payload.get("suspicious_paragraphs", [])
        if item.get("paragraph_index") is not None
    }
    reference_results = sanitized_payload.get("reference_results", [])

    paper_result, _created = PaperDetectionResult.objects.update_or_create(
        detection_task=detection_task,
        defaults={
            "source_file": source_file,
            "paragraph_count": int(document.get("paragraph_count") or len(paragraph_results)),
            "segment_count": int(document.get("segment_count") or len(paragraph_results)),
            "reference_count": int(document.get("reference_count") or len(reference_results)),
            "image_detection_enabled": bool(document.get("image_detection_enabled", True)),
        },
    )

    paper_result.paragraph_results.all().delete()
    PaperParagraphResult.objects.bulk_create(
        [
            PaperParagraphResult(
                paper_detection_result=paper_result,
                paragraph_index=int(item.get("paragraph_index", index)),
                text=item.get("text", ""),
                probability=float(item.get("probability") or 0.0),
                label=item.get("label", ""),
                details=item.get("details"),
                explanation=explanation_map.get(item.get("paragraph_index", index)),
            )
            for index, item in enumerate(paragraph_results)
        ]
    )

    paper_result.reference_results.all().delete()
    PaperReferenceResult.objects.bulk_create(
        [
            PaperReferenceResult(
                paper_detection_result=paper_result,
                reference_index=int(item.get("reference_index", index)),
                reference=item.get("reference", ""),
                exists=bool(item.get("exists", False)),
                is_relevant=bool(item.get("is_relevant", False)),
                overlap_terms=item.get("overlap_terms") or [],
            )
            for index, item in enumerate(reference_results)
        ]
    )
    return sanitized_payload


def store_review_task_results(*, detection_task, paper_file, review_file, results_payload):
    sanitized_payload = sanitize_json_like(results_payload)
    document = sanitized_payload.get("document", {})
    paragraph_results = sanitized_payload.get("paragraph_results", [])
    review_analysis = sanitized_payload.get("review_analysis_results") or {}
    overall_evaluation = review_analysis.get("overall") or sanitized_payload.get("overall_evaluation") or {}
    analysis_map = {
        item.get("review_paragraph_index"): item
        for item in review_analysis.get("paragraph_results", [])
        if item.get("review_paragraph_index") is not None
    }

    review_result, _created = ReviewDetectionResult.objects.update_or_create(
        detection_task=detection_task,
        defaults={
            "paper_file": paper_file,
            "review_file": review_file,
            "paper_segment_count": int(document.get("paper_segment_count") or 0),
            "review_segment_count": int(document.get("review_segment_count") or len(paragraph_results)),
        },
    )

    review_result.paragraph_results.all().delete()
    ReviewParagraphResult.objects.bulk_create(
        [
            ReviewParagraphResult(
                review_detection_result=review_result,
                paragraph_index=int(item.get("paragraph_index", index)),
                text=item.get("text", ""),
                probability=float(item.get("probability") or 0.0),
                label=item.get("label", ""),
                details=item.get("details"),
                suspicious_explanation=(item.get("details") or {}).get("explanation"),
                paper_paragraph_index=_coerce_optional_int(
                    analysis_map.get(item.get("paragraph_index", index), {}).get("paper_paragraph_index")
                ),
                paper_text="",
                relevance_score=_coerce_optional_float(
                    analysis_map.get(item.get("paragraph_index", index), {}).get("relevance_score")
                ),
                relevance_label=analysis_map.get(item.get("paragraph_index", index), {}).get("relevance_level", ""),
                relevance_explanation=analysis_map.get(item.get("paragraph_index", index), {}).get("explanation"),
            )
            for index, item in enumerate(paragraph_results)
        ]
    )
    return sanitized_payload


def get_task_results_payload(task):
    if task.task_type == "paper":
        return get_paper_task_results_payload(task)
    if task.task_type == "review":
        return get_review_task_results_payload(task)
    return None


def get_paper_task_results_payload(task):
    raw_payload = sanitize_json_like(task.text_detection_results or {})
    try:
        paper_result = task.paper_detection_result
    except PaperDetectionResult.DoesNotExist:
        return raw_payload

    paragraph_results = [
        {
            "paragraph_index": item.paragraph_index,
            "text": item.text,
            "probability": item.probability,
            "label": item.label,
            "details": item.details or {},
        }
        for item in paper_result.paragraph_results.all().order_by("paragraph_index")
    ]
    suspicious_paragraphs = [
        {
            "paragraph_index": item.paragraph_index,
            "probability": item.probability,
            "explanation": item.explanation,
        }
        for item in paper_result.paragraph_results.all().order_by("paragraph_index")
        if item.explanation
    ]
    raw_reference_map = {
        int(item.get("reference_index")): item
        for item in (raw_payload.get("reference_results") or [])
        if item.get("reference_index") is not None
    }
    reference_results = [
        {
            "reference_index": item.reference_index,
            "reference": item.reference,
            "exists": item.exists,
            "is_relevant": item.is_relevant,
            "overlap_terms": item.overlap_terms or [],
            "authenticity_score": raw_reference_map.get(item.reference_index, {}).get("authenticity_score"),
            "authenticity_label": raw_reference_map.get(item.reference_index, {}).get("authenticity_label"),
            "authenticity_reason": raw_reference_map.get(item.reference_index, {}).get("authenticity_reason"),
        }
        for item in paper_result.reference_results.all().order_by("reference_index")
    ]
    image_results = [
        {
            "image_id": result.image_upload_id,
            "page_number": result.image_upload.page_number,
            "status": result.status,
            "is_fake": result.is_fake,
            "confidence_score": result.confidence_score,
        }
        for result in DetectionResult.objects.filter(detection_task=task)
        .select_related("image_upload")
        .order_by("image_upload_id")
    ]

    confirmed_ai_paragraphs = raw_payload.get("confirmed_ai_paragraphs") or [
        {
            "paragraph_index": item.paragraph_index,
            "probability": item.probability,
            "reason": (item.details or {}).get("forgery_reason"),
        }
        for item in paper_result.paragraph_results.all().order_by("paragraph_index")
        if bool((item.details or {}).get("is_ai_confirmed"))
    ]

    return sanitize_json_like(
        {
            "document": {
                "file_id": paper_result.source_file_id,
                "file_name": paper_result.source_file.file_name if paper_result.source_file else "",
                "paragraph_count": paper_result.paragraph_count,
                "segment_count": paper_result.segment_count,
                "reference_count": paper_result.reference_count,
                "image_detection_enabled": paper_result.image_detection_enabled,
            },
            "paragraph_results": paragraph_results,
            "confirmed_ai_paragraphs": confirmed_ai_paragraphs,
            "suspicious_paragraphs": suspicious_paragraphs,
            "reference_results": reference_results,
            "data_authenticity_results": raw_payload.get("data_authenticity_results") or {"summary": "-", "findings": []},
            "overall_evaluation": raw_payload.get("overall_evaluation") or {},
            "image_results": image_results,
        }
    )


def get_review_task_results_payload(task):
    raw_payload = sanitize_json_like(task.text_detection_results or {})
    try:
        review_result = task.review_detection_result
    except ReviewDetectionResult.DoesNotExist:
        return raw_payload

    paragraph_rows = list(review_result.paragraph_results.all().order_by("paragraph_index"))
    paragraph_results = [
        {
            "paragraph_index": item.paragraph_index,
            "text": item.text,
            "probability": item.probability,
            "label": item.label,
            "details": item.details or {},
        }
        for item in paragraph_rows
    ]
    review_analysis_results = sanitize_json_like(raw_payload.get("review_analysis_results") or {
        "overall": raw_payload.get("overall_evaluation") or {},
        "paragraph_results": [],
    })
    suspicious_paragraphs = [
        {
            "paragraph_index": item.paragraph_index,
            "probability": item.probability,
            "explanation": item.suspicious_explanation,
        }
        for item in paragraph_rows
        if item.suspicious_explanation
    ]
    relevance_results = [
        {
            "review_paragraph_index": item.paragraph_index,
            "review_text": item.text,
            "paper_paragraph_index": item.paper_paragraph_index,
            "paper_text": item.paper_text,
            "relevance_score": item.relevance_score,
            "label": item.relevance_label,
            "explanation": item.relevance_explanation,
            "template_like_level": (item.details or {}).get("template_like_level"),
            "wrongness_level": (item.details or {}).get("wrongness_level"),
        }
        for item in paragraph_rows
        if item.relevance_score is not None or item.relevance_explanation or item.details
    ]

    return sanitize_json_like(
        {
            "document": {
                "paper_file_id": review_result.paper_file_id,
                "paper_file_name": review_result.paper_file.file_name if review_result.paper_file else "",
                "review_file_id": review_result.review_file_id,
                "review_file_name": review_result.review_file.file_name if review_result.review_file else "",
                "paper_segment_count": review_result.paper_segment_count,
                "review_segment_count": review_result.review_segment_count,
                "paper_paragraph_count": raw_payload.get("document", {}).get("paper_paragraph_count"),
                "review_paragraph_count": raw_payload.get("document", {}).get("review_paragraph_count"),
            },
            "paragraph_results": paragraph_results,
            "suspicious_paragraphs": suspicious_paragraphs,
            "relevance_results": relevance_results,
            "review_analysis_results": review_analysis_results,
            "overall_evaluation": review_analysis_results.get("overall") or {},
        }
    )


def _coerce_optional_int(value):
    if value is None or value == "":
        return None
    return int(value)


def _coerce_optional_float(value):
    if value is None or value == "":
        return None
    return float(value)
