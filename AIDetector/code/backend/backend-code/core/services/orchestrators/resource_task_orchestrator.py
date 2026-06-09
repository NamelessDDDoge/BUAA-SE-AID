import os
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, transaction
from django.utils import timezone

from ..event_logger import log_user_event
from ...models import DetectionTask, FileManagement
from .paper_task_orchestrator import run_paper_detection_task
from .review_task_orchestrator import run_review_detection_task


def _get_resource_task_max_workers():
    raw = os.environ.get("RESOURCE_TASK_MAX_WORKERS", "2")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 2
    return max(1, value)


RESOURCE_TASK_EXECUTOR = ThreadPoolExecutor(
    max_workers=_get_resource_task_max_workers(),
    thread_name_prefix="resource-detection-task",
)

LLM_RESOURCE_TASK_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="resource-detection-task-llm",
)


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
    llm_model_name=None,
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
        status="pending",
        if_use_llm=effective_if_use_llm,
        llm_model_name=llm_model_name,
        method_switches=normalized_switches,
        text_detection_results=initial_text_results,
        progress_percentage=0,
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


def create_resource_detection_tasks(
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
    llm_model_name=None,
    extract_images=None,
    on_commit=None,
    async_task_starter=None,
):
    files = _load_and_validate_resource_files(user=user, task_type=task_type, file_ids=file_ids)
    file_groups = _split_resource_file_groups(task_type=task_type, file_list=files)
    total_groups = len(file_groups)
    if total_groups > 1:
        if task_type == "paper" and _has_text_overrides(text_override=text_override, paper_text_override=paper_text_override):
            raise ValueError("Text overrides are only supported for a single paper resource task")
        if task_type == "review" and _has_text_overrides(text_override=text_override, review_text_override=review_text_override):
            raise ValueError("Review text overrides are only supported for a single review resource task")

    created_tasks = []
    created_file_lists = []
    with transaction.atomic():
        for index, file_group in enumerate(file_groups):
            group_task_name = _build_split_task_name(
                task_type=task_type,
                base_task_name=task_name,
                file_group=file_group,
                index=index,
                total=total_groups,
            )
            detection_task, created_files = create_resource_detection_task(
                user=user,
                task_type=task_type,
                file_ids=[file_record.id for file_record in file_group],
                task_name=group_task_name,
                api_key=api_key,
                text_override=text_override,
                paper_text_override=paper_text_override,
                review_text_override=review_text_override,
                if_use_llm=if_use_llm,
                method_switches=method_switches,
                llm_model_name=llm_model_name,
                extract_images=extract_images,
                on_commit=on_commit,
                async_task_starter=async_task_starter,
            )
            created_tasks.append(detection_task)
            created_file_lists.append(created_files)

    return created_tasks, created_file_lists


def _has_text_overrides(*, text_override=None, paper_text_override=None, review_text_override=None):
    return any(
        isinstance(value, str) and bool(value.strip())
        for value in (text_override, paper_text_override, review_text_override)
    )


def run_resource_detection_task_async(task_type, task_id, api_key=None):
    close_old_connections()
    try:
        resume = _mark_resource_task_started(task_id)
        task_runner = _get_resource_task_runner(task_type)
        task_runner(task_id, api_key=api_key, resume=resume)
    except Exception as exc:
        detection_task = DetectionTask.objects.filter(pk=task_id).first()
        if detection_task is not None:
            detection_task.status = "failed"
            detection_task.error_message = str(exc)[:2000]
            detection_task.completion_time = timezone.now()
            detection_task.save(update_fields=["status", "error_message", "completion_time"])
    finally:
        close_old_connections()


def _mark_resource_task_started(task_id):
    """
    将任务标记为 in_progress.
    返回 True 表示需要恢复执行（存在 checkpoint 数据），
    返回 False 表示全新启动。
    """
    task = DetectionTask.objects.filter(pk=task_id).only(
        "status", "checkpoint_data", "progress_percentage"
    ).first()
    if not task:
        return False

    # 全新任务：pending → in_progress，重置进度
    if task.status == "pending":
        DetectionTask.objects.filter(pk=task_id).update(
            status="in_progress",
            error_message="",
            progress_percentage=0,
            checkpoint_data=None,
        )
        return False

    # 失败或被中断但有 checkpoint → 恢复执行
    if task.status in ("failed", "in_progress") and task.checkpoint_data:
        DetectionTask.objects.filter(pk=task_id).update(
            status="in_progress",
            error_message="",
        )
        return True

    # 其他情况（已完成等）不处理
    return False


def start_resource_detection_task_thread(task_type, task_id, api_key=None):
    detection_task = DetectionTask.objects.filter(pk=task_id).only("if_use_llm").first()
    use_llm_executor = bool(detection_task and detection_task.if_use_llm)
    executor = LLM_RESOURCE_TASK_EXECUTOR if use_llm_executor else RESOURCE_TASK_EXECUTOR
    return executor.submit(run_resource_detection_task_async, task_type, task_id, api_key)


def _get_resource_task_runner(task_type):
    if task_type == "paper":
        return run_paper_detection_task
    if task_type == "review":
        return run_review_detection_task
    raise ValueError(f"Unsupported resource task type: {task_type}")


def _load_and_validate_resource_files(*, user, task_type, file_ids):
    if task_type not in {"paper", "review"}:
        raise ValueError("task_type must be paper or review")

    if not isinstance(file_ids, list) or not file_ids:
        raise ValueError("file_ids is required and must be a non-empty list")

    files = FileManagement.objects.filter(id__in=file_ids, user=user)
    if files.count() != len(set(file_ids)):
        raise FileNotFoundError("Some files do not exist or do not belong to current user")

    file_list = list(files)
    resource_types = {f.resource_type for f in file_list}

    if task_type == "paper":
        if resource_types != {"paper"}:
            raise ValueError("paper task only accepts paper resource files")
        return sorted(file_list, key=lambda item: item.id)

    if not ({"review_paper", "review_file"} <= resource_types):
        raise ValueError("review task requires both review_paper and review_file")

    review_papers = [f for f in file_list if f.resource_type == "review_paper"]
    if len(review_papers) != 1:
        raise ValueError("review task requires exactly one review_paper file")

    review_paper_ids = {f.id for f in review_papers}
    review_files = [f for f in file_list if f.resource_type == "review_file"]
    if not any(rv.linked_file and rv.linked_file.id in review_paper_ids for rv in review_files):
        raise ValueError("review_file is not correctly linked to review_paper")
    return sorted(file_list, key=lambda item: item.id)


def _split_resource_file_groups(*, task_type, file_list):
    if task_type == "paper":
        return [[file_record] for file_record in file_list]

    paper_files = [file_record for file_record in file_list if file_record.resource_type == "review_paper"]
    review_files = [file_record for file_record in file_list if file_record.resource_type == "review_file"]
    if len(paper_files) != 1:
        raise ValueError("review task requires exactly one review_paper file")

    paper_file = paper_files[0]

    groups = []
    for review_file in review_files:
        linked_paper = review_file.linked_file
        if not linked_paper or linked_paper.id != paper_file.id:
            raise ValueError("review_file is not correctly linked to review_paper")
        groups.append([paper_file, review_file])

    return groups


def _build_split_task_name(*, task_type, base_task_name, file_group, index, total):
    if not base_task_name:
        timestamp = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
        base_task_name = f"论文检测 {timestamp}" if task_type == "paper" else f"Review检测 {timestamp}"

    if total <= 1:
        return base_task_name

    if task_type == "paper":
        suffix = file_group[0].file_name
    else:
        suffix = file_group[1].file_name if len(file_group) > 1 else file_group[0].file_name
    return f"{base_task_name} · {index + 1}/{total} · {suffix}"
