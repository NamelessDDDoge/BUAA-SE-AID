import json
import shutil
import zipfile
from pathlib import Path

import numpy as np
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ....models import DetectionResult, DetectionTask, SubDetectionResult
from ....utils.fanyi import fanyi_text
from ....utils.image_saver import save_ndarray_as_image
from ....utils.report_generator import generate_detection_task_report
from .local_inference_client import get_result


SUB_METHODS = (
    ("urn_coarse_v2", "splicing"),
    ("urn_blurring", "blurring"),
    ("urn_brute_force", "bruteforce"),
    ("urn_contrast", "contrast"),
    ("urn_inpainting", "inpainting"),
)


def execute_detection_task(detection_task, image_uploads):
    detection_results = []
    for image_upload in image_uploads:
        detection_result, _ = DetectionResult.objects.get_or_create(
            image_upload=image_upload,
            detection_task=detection_task,
            defaults={"status": "in_progress"},
        )
        detection_result.status = "in_progress"
        detection_result.save(update_fields=["status"])
        detection_results.append(detection_result)

    if not detection_results:
        return []

    total_images = len(detection_results)
    batch_size = 20
    for batch_start in range(0, total_images, batch_size):
        batch_drs = detection_results[batch_start : batch_start + batch_size]
        batch_dir = _create_batch_inputs(
            detection_task=detection_task,
            batch_index=batch_start // batch_size,
            batch_drs=batch_drs,
        )
        try:
            _run_local_detection_batch(
                detection_result_ids=[dr.id for dr in batch_drs],
                batch_dir=batch_dir,
                image_num=total_images,
                task_pk=detection_task.pk,
            )
        finally:
            _cleanup_batch_dir(batch_dir)

    return detection_results


def _create_batch_inputs(detection_task, batch_index, batch_drs):
    batch_dir = Path(settings.MEDIA_ROOT) / "temp" / f"task_{detection_task.id}_batch_{batch_index}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    zip_path = batch_dir / "img.zip"
    data_path = batch_dir / "data.json"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for detection_result in sorted(batch_drs, key=lambda item: item.image_upload.id):
            source_path = Path(detection_result.image_upload.image.path)
            arcname = f"{int(detection_result.image_upload.id):08d}{source_path.suffix}"
            zip_file.write(source_path, arcname=arcname)

    with data_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "cmd_block_size": detection_task.cmd_block_size,
                "urn_k": detection_task.urn_k,
                "if_use_llm": detection_task.if_use_llm,
                "method_switches": detection_task.method_switches,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )

    return batch_dir


def _run_local_detection_batch(detection_result_ids, batch_dir, image_num, task_pk):
    zip_path = Path(batch_dir) / "img.zip"
    data_path = Path(batch_dir) / "data.json"

    detection_results = list(
        DetectionResult.objects.select_related("detection_task", "image_upload")
        .filter(id__in=detection_result_ids)
        .order_by("image_upload_id", "id")
    )
    if not detection_results:
        return

    task = detection_results[0].detection_task
    if task.status != "in_progress":
        task.status = "in_progress"
        task.error_message = ""
        task.save(update_fields=["status", "error_message"])

    DetectionResult.objects.filter(id__in=detection_result_ids).update(status="in_progress")

    raw_results = get_result(zip_path, data_path)
    if raw_results is None:
        raise RuntimeError("Local image detection did not return a result payload.")

    for index, detection_result in enumerate(detection_results):
        parsed_result = _extract_single_result(raw_results, index)
        _persist_detection_result(detection_result, parsed_result)

    _finalize_detection_task(task_pk, image_num)


def _extract_single_result(raw_results, index):
    result_map = _payload_by_name(raw_results)

    llm_entries = result_map.get("llm", [])
    llm_text = ""
    llm_image = None
    if llm_entries and index < len(llm_entries):
        llm_text, llm_image = _parse_llm_entry(llm_entries[index])

    ela_entries = result_map.get("ela", [])
    ela_result = _extract_second_item(ela_entries, index)
    ela_image = np.asarray(ela_result if ela_result is not None else np.zeros((8, 8), dtype=np.uint8))

    exif_entries = result_map.get("exif", [])
    exif_result = _extract_exif_entry(exif_entries, index)

    sub_method_results = []
    probabilities = []
    for raw_method_name, result_method_name in SUB_METHODS:
        method_entries = result_map.get(raw_method_name, [])
        mask_value, probability = _extract_method_entry(method_entries, index)
        if not method_entries:
            continue
        probabilities.append(float(probability))
        sub_method_results.append(
            {
                "method": result_method_name,
                "prob": float(probability),
                "mask": np.squeeze(np.asarray(mask_value)).tolist(),
            }
        )

    exif_flags = {"photoshop": False, "time_modified": False}
    if exif_result:
        exif_text = " ".join(exif_result) if isinstance(exif_result, (list, tuple)) else str(exif_result)
        lower_exif_text = exif_text.lower()
        exif_flags["photoshop"] = "photoshop" in lower_exif_text
        exif_flags["time_modified"] = "time" in lower_exif_text or "modified" in lower_exif_text

    overall_is_fake = any(prob > 0.5 for prob in probabilities) or bool(exif_result)
    overall_confidence = max(probabilities) if probabilities else 0.0
    if exif_result:
        overall_confidence = 1.0

    return {
        "llm_text": llm_text,
        "llm_img": None if llm_image is None else np.asarray(llm_image),
        "ela": ela_image,
        "overall_is_fake": overall_is_fake,
        "overall_confidence": overall_confidence,
        "exif_flags": exif_flags,
        "sub_method_results": sub_method_results,
    }


def _payload_by_name(raw_results):
    result = {}
    for item in raw_results or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        result[item[0]] = item[1]
    return result


def _extract_second_item(entries, index):
    if not entries or index >= len(entries):
        return None
    entry = entries[index]
    if isinstance(entry, (list, tuple)) and len(entry) > 1:
        return entry[1]
    return entry


def _extract_exif_entry(entries, index):
    if not entries or index >= len(entries):
        return None
    entry = entries[index]
    if isinstance(entry, (list, tuple)) and len(entry) > 1:
        payload = entry[1]
        if isinstance(payload, (list, tuple)) and len(payload) > 1:
            return payload[1]
        return payload
    return entry


def _extract_method_entry(entries, index):
    default_mask = np.zeros((8, 8), dtype=np.float32)
    if entries is None:
        return default_mask, 0.0

    if len(entries) > index and isinstance(entries[index], (list, tuple)) and len(entries[index]) == 2:
        mask_value, probability = entries[index]
        return mask_value, probability

    start = index * 2
    if len(entries) >= start + 2:
        return entries[start], entries[start + 1]

    if len(entries) == 1 and isinstance(entries[0], (list, tuple)):
        nested_entries = entries[0]
        if len(nested_entries) >= start + 2:
            return nested_entries[start], nested_entries[start + 1]

    return default_mask, 0.0


def _parse_llm_entry(llm_entry):
    payload = llm_entry[1] if isinstance(llm_entry, (list, tuple)) and len(llm_entry) > 1 else llm_entry
    if payload is None:
        return "", None
    if isinstance(payload, dict):
        return payload.get("outputs", ""), payload.get("mask")
    if isinstance(payload, (list, tuple)):
        if payload and isinstance(payload[0], dict):
            return payload[0].get("outputs", ""), payload[1] if len(payload) > 1 else None
        if payload and isinstance(payload[0], str):
            return payload[0], payload[1] if len(payload) > 1 else None
    return str(payload), None


def _persist_detection_result(detection_result, parsed_result):
    ela_path = save_ndarray_as_image(
        np.asarray(parsed_result["ela"]),
        subdir="ela_results",
        prefix=f"ela_{detection_result.id}",
    )
    llm_image_path = None
    if parsed_result["llm_img"] is not None:
        llm_image_path = save_ndarray_as_image(
            np.asarray(parsed_result["llm_img"]),
            subdir="llm_results",
            prefix=f"llm_{detection_result.id}",
        )

    detection_result.is_fake = parsed_result["overall_is_fake"]
    detection_result.confidence_score = parsed_result["overall_confidence"]
    detection_result.llm_judgment = fanyi_text(parsed_result["llm_text"])
    detection_result.ela_image = ela_path
    if llm_image_path is not None:
        detection_result.llm_image = llm_image_path
    detection_result.exif_photoshop = parsed_result["exif_flags"]["photoshop"]
    detection_result.exif_time_modified = parsed_result["exif_flags"]["time_modified"]
    detection_result.detection_time = timezone.now()
    detection_result.status = "completed"
    detection_result.save()

    SubDetectionResult.objects.filter(detection_result=detection_result).delete()
    for sub_result in parsed_result["sub_method_results"]:
        mask_array = np.asarray(sub_result["mask"])
        mask_path = save_ndarray_as_image(
            mask_array,
            subdir="masks",
            prefix=f"mask_{sub_result['method']}_{detection_result.id}",
        )
        SubDetectionResult.objects.create(
            detection_result=detection_result,
            method=sub_result["method"],
            probability=sub_result["prob"],
            mask_image=mask_path,
            mask_matrix=json.loads(json.dumps(mask_array.tolist())),
        )

    image_upload = detection_result.image_upload
    image_upload.isFake = detection_result.is_fake
    image_upload.isDetect = True
    image_upload.save(update_fields=["isFake", "isDetect"])


def _finalize_detection_task(task_pk, image_num):
    detection_task = DetectionTask.objects.get(pk=task_pk)
    completed_count = DetectionResult.objects.filter(
        detection_task=detection_task,
        status="completed",
    ).count()
    if completed_count != image_num:
        return

    if detection_task.task_type != "image":
        return

    with transaction.atomic():
        detection_task.status = "completed"
        detection_task.completion_time = timezone.now()
        detection_task.error_message = ""
        detection_task.save(update_fields=["status", "completion_time", "error_message"])
        generate_detection_task_report(detection_task)


def _cleanup_batch_dir(batch_dir):
    batch_dir = Path(batch_dir)
    if batch_dir.exists():
        shutil.rmtree(batch_dir, ignore_errors=True)
