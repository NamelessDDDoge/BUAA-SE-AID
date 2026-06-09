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
from ..capabilities.llm.fastdetect_client import batch_detect_text_segments
from ..capabilities.text_detection_service import (
    DetectionBillingUnavailableError,
    _classify_ai_verdict,
    _build_verdict_reason,
    _is_detection_error,
    preflight_text_detection,
)
from ..resources.document_preprocessor import preprocess_document
from ..resources.document_preprocessor import (
    extract_document_paragraphs,
    extract_document_references,
    split_text_into_segments,
    parse_document_sections,
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

# ---------------------------------------------------------------------------
# Progress weight constants
# - text_analysis base: per-segment granularity (70% split across segments)
# - other steps: whole-step updates
# ---------------------------------------------------------------------------
_STEP_WEIGHTS = {
    "preprocess": 5,
    "text_analysis": 0,       # base — real per-segment weight computed at runtime
    "post_text": 25,          # explanations + references + authenticity + overall + image_detection + save
}

_STEP_ORDER = [
    "preprocess",
    "text_analysis",
    "post_text",
]

_STEP_LABELS = {
    "preprocess": "预处理文档 ...",
    "text_analysis": "AI 文本检测分析 ...",
}


def _save_progress(detection_task, pct, step_name, label=""):
    """保存进度，支持精确百分比。"""
    pct = min(max(pct, 0), 100)
    completed_idx = _STEP_ORDER.index(step_name) if step_name in _STEP_ORDER else -1
    completed = _STEP_ORDER[:completed_idx + 1] if completed_idx >= 0 else []
    now = timezone.now().isoformat()
    # 读取已有的 step_started_at 避免覆盖
    existing_cp = detection_task.checkpoint_data or {}
    step_started = existing_cp.get("step_started_at") or {}
    if step_name not in step_started:
        step_started[step_name] = now
    cp = {
        "step": step_name,
        "completed_steps": completed,
        "step_started_at": step_started,
        "updated_at": now,
    }
    DetectionTask.objects.filter(pk=detection_task.pk).update(
        progress_percentage=pct,
        checkpoint_data=cp,
    )
    detection_task.refresh_from_db(fields=["progress_percentage", "checkpoint_data"])


def _should_skip_step(checkpoint, step_name):
    if not checkpoint:
        return False
    completed = checkpoint.get("completed_steps") or []
    return step_name in completed


def run_paper_detection_task(task_id, api_key=None, resume=False):
    detection_task = DetectionTask.objects.get(id=task_id)

    if not resume:
        detection_task.status = "in_progress"
        detection_task.error_message = ""
        detection_task.progress_percentage = 0
        now_iso = timezone.now().isoformat()
        detection_task.checkpoint_data = {"started_at": now_iso, "updated_at": now_iso, "step_started_at": {}}
        detection_task.save(
            update_fields=["status", "error_message", "progress_percentage", "checkpoint_data"]
        )
    else:
        # 恢复执行时设 resume_at 标记
        now_iso = timezone.now().isoformat()
        cp = detection_task.checkpoint_data or {}
        cp.setdefault("step_started_at", {})
        cp["resumed_at"] = now_iso
        cp["updated_at"] = now_iso
        detection_task.checkpoint_data = cp
        detection_task.save(update_fields=["checkpoint_data"])

    checkpoint = detection_task.checkpoint_data

    paper_files = list(detection_task.resource_files.filter(resource_type="paper").order_by("id"))
    if not paper_files:
        return _mark_task_failed(detection_task, "No paper resource file found")

    try:
        preflight_text_detection(api_key=api_key)
    except DetectionBillingUnavailableError as exc:
        return _mark_task_failed(detection_task, str(exc))

    paper_items = []
    for file_management in paper_files:
        file_path = os.path.join(settings.MEDIA_ROOT, file_management.stored_path)
        if not os.path.exists(file_path):
            return _mark_task_failed(detection_task, "Paper file path does not exist")

        try:
            paper_items.append(
                _run_single_paper_detection_item(
                    detection_task=detection_task,
                    file_management=file_management,
                    file_path=file_path,
                    api_key=api_key,
                    checkpoint=checkpoint,
                )
            )
        except DetectionBillingUnavailableError as exc:
            return _mark_task_failed(detection_task, str(exc))

    if _should_skip_step(checkpoint, "post_text"):
        pass
    else:
        primary_item = paper_items[0]
        aggregated_payload = _build_multi_paper_payload(primary_item, paper_items)

        detection_task.text_detection_results = store_paper_task_results(
            detection_task=detection_task,
            source_file=primary_item["source_file"],
            results_payload=aggregated_payload,
        )
        detection_task.status = "completed"
        detection_task.completion_time = timezone.now()
        detection_task.error_message = ""
        detection_task.progress_percentage = 100
        detection_task.checkpoint_data = {"step": "save", "completed_steps": _STEP_ORDER}
        detection_task.save(
            update_fields=[
                "text_detection_results", "status", "completion_time",
                "error_message", "progress_percentage", "checkpoint_data",
            ]
        )
        generate_task_report(detection_task)

    return "Paper detection finished"


def _run_single_paper_detection_item(*, detection_task, file_management, file_path, api_key=None, checkpoint=None):
    # --- Step 1: 预处理 -------------------------------------------------------
    if _should_skip_step(checkpoint, "preprocess"):
        processed_document = (checkpoint.get("partial") or {}).get("processed_document")
        if not processed_document:
            processed_document = _do_preprocess(detection_task, file_path)
    else:
        _save_progress(detection_task, 5, "preprocess")
        processed_document = _do_preprocess(detection_task, file_path)
        _save_checkpoint_partial(detection_task, {"processed_document": _summarize_doc(processed_document)})

    # --- Step 2: 文本段 AI 检测（逐段更新进度）----------------------------------
    paragraph_results = None
    if _should_skip_step(checkpoint, "text_analysis"):
        paragraph_results = (checkpoint.get("partial") or {}).get("paragraph_results")

    if paragraph_results is None:
        # 全新检测 or partial 数据丢失，从 else 分支执行完整检测
        segment_count = len(processed_document["segments"])
        # 文本检测权重 70% 均分到每个段，预处理 5% 已消耗
        pct_per_segment = (70.0 / segment_count) if segment_count else 70.0
        SUSPICIOUS_THRESHOLD = 0.5
        _CHECKPOINT_INTERVAL = 5  # 每分析 5 段保存一次 checkpoint

        # 并行批量检测：多 key 分片并发，减少串行等待
        # 传递进度回调，让进度条随实际 API 调用完成实时更新
        raw_responses = batch_detect_text_segments(
            processed_document["segments"],
            api_key=api_key,
            progress_callback=lambda done, total: _save_progress(
                detection_task,
                5 + int((done / total) * 70),
                "text_analysis",
            ),
        )

        paragraph_results = []
        for index, (segment, raw) in enumerate(zip(processed_document["segments"], raw_responses)):
            payload = raw.get("data", {}) if raw else {}
            probability = float(payload.get("prob", 0) or 0)
            details = payload.get("details", {})

            detection_error = _is_detection_error(details)
            if detection_error:
                ai_verdict, is_ai_confirmed, confidence_level = ("service_unavailable", False, "unknown")
                label = "unavailable"
            else:
                ai_verdict, is_ai_confirmed, confidence_level = _classify_ai_verdict(probability)
                label = "suspicious" if probability >= SUSPICIOUS_THRESHOLD else "clean"
            reason = _build_verdict_reason(segment, probability, details, ai_verdict)
            merged_details = {
                **(details if isinstance(details, dict) else {"raw_details": details}),
                "ai_verdict": ai_verdict,
                "is_ai_confirmed": is_ai_confirmed,
                "confidence_level": confidence_level,
                "forgery_reason": reason,
            }
            paragraph_results.append({
                "paragraph_index": index,
                "text": segment,
                "probability": probability,
                "label": label,
                "details": merged_details,
                "ai_verdict": ai_verdict,
                "is_ai_confirmed": is_ai_confirmed,
                "forgery_reason": reason,
            })
            # 定期保存已分析的段到 checkpoint，支持中断恢复
            if (index + 1) % _CHECKPOINT_INTERVAL == 0 or (index + 1) == segment_count:
                _save_checkpoint_partial(detection_task, {"paragraph_results": paragraph_results})

        # 确保 text_analysis 完成后 paragraph_results 在 checkpoint 中
        _save_checkpoint_partial(detection_task, {"paragraph_results": paragraph_results})

    confirmed_ai_paragraphs = [
        {
            "paragraph_index": item.get("paragraph_index"),
            "probability": item.get("probability"),
            "reason": item.get("forgery_reason") or (item.get("details") or {}).get("forgery_reason"),
        }
        for item in paragraph_results
        if bool(item.get("is_ai_confirmed"))
    ]

    # --- 文本检测完成，进度 75% — 后续步骤（解释、参考文献、真实性、评价、图像检测、保存）分剩下的 25% ---
    # 每完成一步前进：
    # explanations(5) → references(5) → authenticity(4) → overall(4) → image(4) → save(3)

    _save_progress(detection_task, 75, "post_text")

    # --- Step 3: 可疑段落解释 -------------------------------------------------
    explanations = build_suspicious_paragraph_explanations(
        paragraph_results, api_key=api_key, llm_model_name=detection_task.llm_model_name,
    )
    _save_progress(detection_task, 80, "post_text")

    # --- Step 4: 参考文献真实性检查 -------------------------------------------
    reference_results = evaluate_references(
        text_content=processed_document["text_content"],
        references=processed_document["references"],
        api_key=api_key,
        llm_model_name=detection_task.llm_model_name,
    )
    _save_progress(detection_task, 85, "post_text")

    # --- Step 5: 数据真实性评估 -----------------------------------------------
    data_authenticity_results = _run_data_authenticity_analysis(
        paragraph_results,
        tables=processed_document.get("tables") or [],
        api_key=api_key,
        llm_model_name=detection_task.llm_model_name,
    )
    _save_progress(detection_task, 89, "post_text")

    # --- Step 6: 综合评价 -----------------------------------------------------
    overall_evaluation = build_overall_paper_evaluation(
        paragraph_results=paragraph_results,
        confirmed_ai_paragraphs=confirmed_ai_paragraphs,
        reference_results=reference_results,
        data_authenticity_results=data_authenticity_results,
        api_key=api_key, llm_model_name=detection_task.llm_model_name,
    )
    _save_progress(detection_task, 93, "post_text")

    # --- Step 7: 论文图像检测 -------------------------------------------------
    image_results = _run_paper_image_detection(detection_task, file_management)
    _save_progress(detection_task, 97, "post_text")

    return {
        "source_file": file_management,
        "document": {
            "file_id": file_management.id,
            "file_name": file_management.file_name,
            "paragraph_count": len(processed_document["paragraphs"]),
            "segment_count": len(processed_document["segments"]),
            "reference_count": len(processed_document["references"]),
            "table_count": len(processed_document.get("tables") or []),
            "image_detection_enabled": _paper_image_detection_enabled(detection_task),
        },
        "paragraph_results": paragraph_results,
        "confirmed_ai_paragraphs": confirmed_ai_paragraphs,
        "suspicious_paragraphs": explanations,
        "reference_results": reference_results,
        "table_results": data_authenticity_results.get("table_results", []),
        "data_authenticity_results": data_authenticity_results,
        "overall_evaluation": overall_evaluation,
        "image_results": image_results,
    }


def _do_preprocess(detection_task, file_path):
    processed_document = preprocess_document(file_path)
    override_text = _get_text_override(detection_task)
    if override_text:
        sanitized_text = sanitize_text_content(override_text)
        sections = parse_document_sections(sanitized_text)
        core_text = sections.get("abstract", "") + "\n\n" + sections.get("body", "") + "\n\n" + sections.get("acknowledgements", "")
        core_text = core_text.strip()

        if not core_text:
            core_text = sanitized_text

        processed_document = {
            "text_content": sanitized_text,
            "paragraphs": extract_document_paragraphs(core_text),
            "sections": sections,
            "references": extract_document_references(sanitized_text),
            "segments": split_text_into_segments(core_text),
        }
    else:
        processed_document["paragraphs"] = extract_document_paragraphs(
            processed_document["sections"].get("abstract", "") + "\n\n" +
            processed_document["sections"].get("body", "") + "\n\n" +
            processed_document["sections"].get("acknowledgements", "")
        )
    return processed_document


def _summarize_doc(processed_document):
    return {
        "text_content": processed_document.get("text_content", "")[:500],
        "paragraphs_count": len(processed_document.get("paragraphs", [])),
        "segments_count": len(processed_document.get("segments", [])),
        "references_count": len(processed_document.get("references", [])),
    }


def _save_checkpoint_partial(detection_task, partial_data):
    cp = detection_task.checkpoint_data or {}
    partial = cp.get("partial") or {}
    partial.update(partial_data)
    cp["partial"] = partial
    DetectionTask.objects.filter(pk=detection_task.pk).update(checkpoint_data=cp)
    detection_task.refresh_from_db(fields=["checkpoint_data"])


def _build_multi_paper_payload(primary_item, paper_items):
    primary_payload = {
        key: value
        for key, value in primary_item.items()
        if key != "source_file"
    }
    return {
        **primary_payload,
        "items": [
            {
                key: value
                for key, value in item.items()
                if key != "source_file"
            }
            for item in paper_items
        ],
        "document": {
            **primary_payload.get("document", {}),
            "resource_count": len(paper_items),
        },
    }


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


def _paper_data_authenticity_enabled():
    return bool(getattr(settings, "ENABLE_PAPER_DATA_AUTHENTICITY_ANALYSIS", False))


def _run_data_authenticity_analysis(paragraph_results, *, tables=None, api_key=None, llm_model_name=None):
    if not _paper_data_authenticity_enabled():
        return {
            "enabled": False,
            "summary": "论文数据真实性分析已关闭。",
            "summary_source": "disabled",
            "summary_risk_level": "none",
            "summary_key_points": [],
            "findings": [],
            "table_results": [],
        }

    results = evaluate_data_authenticity(
        paragraph_results,
        tables=tables or [],
        api_key=api_key,
        llm_model_name=llm_model_name,
    )
    if not isinstance(results, dict):
        results = {
            "summary": "论文数据真实性分析未返回有效结果。",
            "findings": [],
            "table_results": [],
        }
    return {
        "enabled": True,
        "summary": results.get("summary") or "暂无数据真实性分析摘要。",
        "summary_source": results.get("summary_source") or "rule_based",
        "summary_risk_level": results.get("summary_risk_level") or "none",
        "summary_key_points": results.get("summary_key_points") or [],
        "findings": results.get("findings") or [],
        "table_results": results.get("table_results") or [],
        "llm_error": results.get("llm_error"),
        "summary_error": results.get("summary_error"),
    }


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
