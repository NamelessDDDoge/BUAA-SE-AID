import threading

from django.db import close_old_connections, transaction
from django.utils import timezone

from ..event_logger import log_user_event
from ...models import DetectionTask, FileManagement
from .paper_task_orchestrator import run_paper_detection_task
from .review_task_orchestrator import run_review_detection_task


def _normalize_resource_method_switches(method_switches):
    if method_switches is None:
        return None
    if not isinstance(method_switches, dict):
        raise ValueError("method_switches must be an object")
    return {str(key): bool(value) for key, value in method_switches.items()}


def create_resource_detection_task(
    *,
    user,
    task_type,
    file_ids,
    task_name="",
    api_key=None,
    text_override=None,
    paper_text_override=None,
    review_text_override=None,
    if_use_llm=False,
    method_switches=None,
    extract_images=None,
    on_commit=None,
    async_task_starter=None,
):
    if task_type not in {"paper", "review"}:
        raise ValueError("task_type must be paper or review")

    if not isinstance(file_ids, list) or not file_ids:
        raise ValueError("file_ids is required and must be a non-empty list")

    if not task_name:
        timestamp = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
        task_name = f"论文检测 {timestamp}" if task_type == "paper" else f"Review检测 {timestamp}"

    files = FileManagement.objects.filter(id__in=file_ids, user=user)
    if files.count() != len(set(file_ids)):
        raise FileNotFoundError("Some files do not exist or do not belong to current user")

    file_list = list(files)
    resource_types = {f.resource_type for f in file_list}

    if task_type == "paper":
        if resource_types != {"paper"}:
            raise ValueError("paper task only accepts paper resource files")
    else:
        if not ({"review_paper", "review_file"} <= resource_types):
            raise ValueError("review task requires both review_paper and review_file")

        review_paper_ids = {f.id for f in file_list if f.resource_type == "review_paper"}
        review_files = [f for f in file_list if f.resource_type == "review_file"]
        if not any(rv.linked_file and rv.linked_file.id in review_paper_ids for rv in review_files):
            raise ValueError("review_file is not correctly linked to review_paper")

    normalized_switches = _normalize_resource_method_switches(method_switches)
    if task_type == "paper" and extract_images is not None:
        normalized_switches = normalized_switches or {}
        normalized_switches["__paper_extract_images__"] = bool(extract_images)

    effective_if_use_llm = bool(if_use_llm)
    if normalized_switches:
        effective_if_use_llm = effective_if_use_llm or bool(normalized_switches.get("llm"))

    task_status = "in_progress" if async_task_starter is not None else "pending"

    initial_text_results = None
    if task_type == "paper" and isinstance(text_override, str):
        normalized_text = text_override.strip()
        if normalized_text:
            initial_text_results = {"text_override": normalized_text, "paper_text_override": normalized_text}
    elif task_type == "review":
        initial_text_results = {}
        if isinstance(text_override, str) and text_override.strip():
            initial_text_results["review_text_override"] = text_override.strip()
        if isinstance(paper_text_override, str) and paper_text_override.strip():
            initial_text_results["paper_text_override"] = paper_text_override.strip()
        if isinstance(review_text_override, str) and review_text_override.strip():
            initial_text_results["review_text_override"] = review_text_override.strip()
        if not initial_text_results:
            initial_text_results = None

    detection_task = DetectionTask.objects.create(
        organization=user.organization,
        user=user,
        task_type=task_type,
        task_name=task_name,
        status=task_status,
        if_use_llm=effective_if_use_llm,
        method_switches=normalized_switches,
        text_detection_results=initial_text_results,
    )
    detection_task.resource_files.add(*file_list)

    log_user_event(
        user=user,
        operation_type="detection",
        related_model="DetectionTask",
        related_id=detection_task.id,
    )

    commit_hook = on_commit or transaction.on_commit
    if async_task_starter is not None:
        commit_hook(lambda: async_task_starter(task_type, detection_task.id, api_key))
        return detection_task, file_list

    return detection_task, file_list


def run_resource_detection_task_async(task_type, task_id, api_key=None):
    close_old_connections()
    try:
        task_runner = _get_resource_task_runner(task_type)
        task_runner(task_id, api_key=api_key)
    except Exception as exc:
        detection_task = DetectionTask.objects.filter(pk=task_id).first()
        if detection_task is not None:
            detection_task.status = "failed"
            detection_task.error_message = str(exc)[:2000]
            detection_task.completion_time = timezone.now()
            detection_task.save(update_fields=["status", "error_message", "completion_time"])
    finally:
        close_old_connections()


def start_resource_detection_task_thread(task_type, task_id, api_key=None):
    thread = threading.Thread(
        target=run_resource_detection_task_async,
        args=(task_type, task_id, api_key),
        daemon=True,
        name=f"{task_type}-task-{task_id}",
    )
    thread.start()


def _get_resource_task_runner(task_type):
    if task_type == "paper":
        return run_paper_detection_task
    if task_type == "review":
        return run_review_detection_task
    raise ValueError(f"Unsupported resource task type: {task_type}")
