import threading

from django.db import close_old_connections, transaction
from django.utils import timezone

from ...models import DetectionResult, DetectionTask, ImageUpload
from ..capabilities.image_detection_service import run_image_detection_task
from ..event_logger import log_user_event


def _refund_detection_usage(organization, if_use_llm, num_images):
    if organization is None or num_images <= 0:
        return
    if if_use_llm:
        organization.add_llm_uses(num_images)
    else:
        organization.add_non_llm_uses(num_images)


def _mark_detection_task_failed(detection_task, error_message):
    DetectionResult.objects.filter(
        detection_task=detection_task,
        status="in_progress",
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


def _reserve_detection_usage(organization, if_use_llm, num_images):
    organization.reset_usage()
    if if_use_llm:
        if not organization.can_use_llm(num_images):
            raise ValueError(
                "You have exceeded your LLM method usage limit for this week. "
                f"Your organization can only submit {organization.remaining_llm_uses} more images."
            )
        organization.decrement_llm_uses(num_images)
        return

    if not organization.can_use_non_llm(num_images):
        raise ValueError(
            "You have exceeded your non-LLM method usage limit for this week. "
            f"Your organization can only submit {organization.remaining_non_llm_uses} more images."
        )
    organization.decrement_non_llm_uses(num_images)


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
    on_commit=None,
    async_task_starter=None,
):
    if not task_name:
        task_name = "New Detection Task"

    normalized_switches = _normalize_method_switches(method_switches)
    effective_if_use_llm = bool(if_use_llm) or int(mode) == 3
    image_uploads = _validate_image_uploads(user, image_ids)
    num_images = len(image_uploads)
    image_id_list = [image.id for image in image_uploads]

    _reserve_detection_usage(user.organization, effective_if_use_llm, num_images)

    commit_hook = on_commit or transaction.on_commit
    task_starter = async_task_starter or start_image_detection_task_thread

    with transaction.atomic():
        detection_task = DetectionTask.objects.create(
            organization=user.organization,
            user=user,
            task_type="image",
            task_name=task_name,
            status="in_progress",
            cmd_block_size=cmd_block_size,
            urn_k=urn_k,
            if_use_llm=effective_if_use_llm,
            method_switches=normalized_switches,
        )
        detection_task.resource_files.add(*list({img.file_management for img in image_uploads}))

        DetectionResult.objects.bulk_create(
            [
                DetectionResult(
                    image_upload=image_upload,
                    detection_task=detection_task,
                    status="in_progress",
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

    return detection_task, image_uploads


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
    thread = threading.Thread(
        target=runner,
        args=(task_id, image_ids, if_use_llm, num_images),
        daemon=True,
        name=f"detection-task-{task_id}",
    )
    thread.start()
