import os
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, transaction
from django.db.models import F
from django.utils import timezone

from ...models import DetectionResult, DetectionTask, ImageUpload
from ..capabilities.image_detection_service import run_image_detection_task
from ..event_logger import log_user_event


def _get_image_task_max_workers():
    raw = os.environ.get("IMAGE_TASK_MAX_WORKERS", "1")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 2
    return max(1, value)


IMAGE_TASK_EXECUTOR = ThreadPoolExecutor(
    max_workers=_get_image_task_max_workers(),
    thread_name_prefix="image-detection-task",
)

LLM_IMAGE_TASK_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="image-detection-task-llm",
)


def _refund_detection_usage(organization, if_use_llm, num_images):
    if organization is None or num_images <= 0:
        return
    field_name = "remaining_llm_uses" if if_use_llm else "remaining_non_llm_uses"
    updated = type(organization).objects.filter(pk=organization.pk).update(
        **{field_name: F(field_name) + num_images}
    )
    if updated:
        organization.refresh_from_db(fields=[field_name])


def _refresh_usage_field(organization, if_use_llm):
    field_name = "remaining_llm_uses" if if_use_llm else "remaining_non_llm_uses"
    organization.refresh_from_db(fields=[field_name])


def _get_remaining_usage(organization, if_use_llm):
    if if_use_llm:
        return organization.remaining_llm_uses
    return organization.remaining_non_llm_uses


def _mark_detection_task_failed(detection_task, error_message):
    DetectionResult.objects.filter(
        detection_task=detection_task,
        status__in=["pending", "in_progress"],
    ).update(status="failed")
    detection_task.status = "failed"
    detection_task.error_message = (error_message or "")[:2000]
    detection_task.completion_time = timezone.now()
    detection_task.save(update_fields=["status", "error_message", "completion_time"])


def _normalize_method_switches(method_switches):
    if method_switches is None:
        return None
    if not isinstance(method_switches, dict):
        raise ValueError("method_switches must be an object")
    return {str(key): bool(value) for key, value in method_switches.items()}


def _validate_image_method_switches(method_switches):
    if method_switches is None:
        return
    if not any(method_switches.values()):
        raise ValueError("At least one image detection method must be selected")


def _validate_image_uploads(user, image_ids):
    if not isinstance(image_ids, list) or not image_ids:
        raise ValueError("No image IDs provided")

    image_id_list = sorted(int(image_id) for image_id in image_ids)
    image_uploads = list(
        ImageUpload.objects.filter(id__in=image_id_list, file_management__user=user).order_by("id")
    )
    if not image_uploads:
        raise FileNotFoundError("No valid images found")
    return image_uploads


def _mark_image_task_started(detection_task):
    updated = DetectionTask.objects.filter(pk=detection_task.pk, status="pending").update(
        status="in_progress",
        error_message="",
    )
    if updated != 1:
        return False
    detection_task.status = "in_progress"
    detection_task.error_message = ""
    DetectionResult.objects.filter(
        detection_task=detection_task,
        status="pending",
    ).update(status="in_progress")
    return True


def _reserve_detection_usage(organization, if_use_llm, num_images):
    if organization is None:
        raise ValueError("User organization is required")
    if num_images <= 0:
        return
    organization.reset_usage()
    field_name = "remaining_llm_uses" if if_use_llm else "remaining_non_llm_uses"
    updated = type(organization).objects.filter(
        pk=organization.pk,
        **{f"{field_name}__gte": num_images},
    ).update(**{field_name: F(field_name) - num_images})
    _refresh_usage_field(organization, if_use_llm)
    if updated == 1:
        return

    if if_use_llm:
        raise ValueError(
            "You have exceeded your LLM method usage limit for this week. "
            f"Your organization can only submit {_get_remaining_usage(organization, if_use_llm)} more images."
        )

    raise ValueError(
        "You have exceeded your non-LLM method usage limit for this week. "
        f"Your organization can only submit {_get_remaining_usage(organization, if_use_llm)} more images."
    )


def create_image_detection_task(
    *,
    user,
    image_ids,
    task_name="",
    mode=1,
    cmd_block_size=64,
    urn_k=0.3,
    if_use_llm=False,
    method_switches=None,
    llm_model_name=None,
    on_commit=None,
    async_task_starter=None,
):
    if not task_name:
        task_name = "New Detection Task"

    normalized_switches = _normalize_method_switches(method_switches)
    _validate_image_method_switches(normalized_switches)
    effective_if_use_llm = bool(if_use_llm) or int(mode) == 3
    image_uploads = _validate_image_uploads(user, image_ids)
    num_images = len(image_uploads)
    image_id_list = [image.id for image in image_uploads]

    _reserve_detection_usage(user.organization, effective_if_use_llm, num_images)

    commit_hook = on_commit or transaction.on_commit
    task_starter = async_task_starter or start_image_detection_task_thread

    try:
        with transaction.atomic():
            detection_task = DetectionTask.objects.create(
                organization=user.organization,
                user=user,
                task_type="image",
                task_name=task_name,
                status="pending",
                cmd_block_size=cmd_block_size,
                urn_k=urn_k,
                if_use_llm=effective_if_use_llm,
                llm_model_name=llm_model_name,
                method_switches=normalized_switches,
            )
            detection_task.resource_files.add(*list({img.file_management for img in image_uploads}))

            DetectionResult.objects.bulk_create(
                [
                    DetectionResult(
                        image_upload=image_upload,
                        detection_task=detection_task,
                        status="pending",
                    )
                    for image_upload in image_uploads
                ]
            )

            log_user_event(
                user=user,
                operation_type="detection",
                related_model="DetectionTask",
                related_id=detection_task.id,
            )

            commit_hook(
                lambda: task_starter(
                    detection_task.id,
                    image_id_list,
                    effective_if_use_llm,
                    num_images,
                )
            )
    except Exception:
        _refund_detection_usage(user.organization, effective_if_use_llm, num_images)
        raise

    return detection_task, image_uploads


def create_image_detection_tasks(
    *,
    user,
    image_ids,
    task_name="",
    mode=1,
    cmd_block_size=64,
    urn_k=0.3,
    if_use_llm=False,
    method_switches=None,
    llm_model_name=None,
    on_commit=None,
    async_task_starter=None,
):
    if not task_name:
        task_name = "New Detection Task"

    normalized_switches = _normalize_method_switches(method_switches)
    _validate_image_method_switches(normalized_switches)
    effective_if_use_llm = bool(if_use_llm) or int(mode) == 3
    image_uploads = _validate_image_uploads(user, image_ids)
    total_images = len(image_uploads)
    _reserve_detection_usage(user.organization, effective_if_use_llm, total_images)

    commit_hook = on_commit or transaction.on_commit
    task_starter = async_task_starter or start_image_detection_task_thread

    created_tasks = []
    created_upload_groups = []
    try:
        with transaction.atomic():
            for index, image_upload in enumerate(image_uploads):
                split_task_name = _build_split_image_task_name(
                    base_task_name=task_name,
                    image_upload=image_upload,
                    index=index,
                    total=total_images,
                )
                detection_task = DetectionTask.objects.create(
                    organization=user.organization,
                    user=user,
                    task_type="image",
                    task_name=split_task_name,
                    status="pending",
                    cmd_block_size=cmd_block_size,
                    urn_k=urn_k,
                    if_use_llm=effective_if_use_llm,
                    llm_model_name=llm_model_name,
                    method_switches=normalized_switches,
                )
                detection_task.resource_files.add(image_upload.file_management)
                DetectionResult.objects.create(
                    image_upload=image_upload,
                    detection_task=detection_task,
                    status="pending",
                )
                log_user_event(
                    user=user,
                    operation_type="detection",
                    related_model="DetectionTask",
                    related_id=detection_task.id,
                )
                image_id_list = [image_upload.id]
                commit_hook(
                    lambda task_id=detection_task.id, ids=image_id_list: task_starter(
                        task_id,
                        ids,
                        effective_if_use_llm,
                        1,
                    )
                )
                created_tasks.append(detection_task)
                created_upload_groups.append([image_upload])
    except Exception:
        _refund_detection_usage(user.organization, effective_if_use_llm, total_images)
        raise

    return created_tasks, created_upload_groups


def run_image_detection_task_async(
    task_id,
    image_ids,
    if_use_llm,
    num_images,
    *,
    detection_executor=None,
):
    close_old_connections()
    executor = detection_executor or run_image_detection_task
    try:
        detection_task = DetectionTask.objects.select_related("organization").get(pk=task_id)
        if not _mark_image_task_started(detection_task):
            return
        image_uploads = list(
            ImageUpload.objects.filter(id__in=image_ids, file_management__user=detection_task.user).order_by("id")
        )
        if not image_uploads:
            raise RuntimeError("No valid images found")
        executor(detection_task=detection_task, image_uploads=image_uploads)
    except Exception as exc:
        detection_task = DetectionTask.objects.select_related("organization").filter(pk=task_id).first()
        if detection_task is not None:
            _refund_detection_usage(detection_task.organization, if_use_llm, num_images)
            _mark_detection_task_failed(detection_task, str(exc))
    finally:
        close_old_connections()


def start_image_detection_task_thread(task_id, image_ids, if_use_llm, num_images, *, task_runner=None):
    runner = task_runner or run_image_detection_task_async
    executor = LLM_IMAGE_TASK_EXECUTOR if if_use_llm else IMAGE_TASK_EXECUTOR
    return executor.submit(
        runner,
        task_id,
        image_ids,
        if_use_llm,
        num_images,
    )


def _build_split_image_task_name(*, base_task_name, image_upload, index, total):
    if not base_task_name:
        timestamp = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
        base_task_name = f"图像检测 {timestamp}"
    if total <= 1:
        return base_task_name
    file_name = getattr(image_upload.file_management, "file_name", "") or f"image_{image_upload.id}"
    return f"{base_task_name} · {index + 1}/{total} · {file_name}"
