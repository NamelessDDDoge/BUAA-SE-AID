"""orchestrators/image_task_orchestrator"""
from unittest.mock import MagicMock

import pytest
from django.test import override_settings

from core.models import DetectionResult, DetectionTask
from core.services.orchestrators import image_task_orchestrator as orch
from core.tests.factories import (
    make_detection_task,
    make_image_upload,
    make_organization,
    make_user,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# ---------- _normalize_method_switches ----------

def test_normalize_method_switches_returns_none_when_input_none():
    assert orch._normalize_method_switches(None) is None


def test_normalize_method_switches_coerces_str_keys_and_bool_values():
    out = orch._normalize_method_switches({"ela": 1, 5: ""})
    assert out == {"ela": True, "5": False}


def test_normalize_method_switches_rejects_non_dict():
    with pytest.raises(ValueError, match="method_switches must be an object"):
        orch._normalize_method_switches([("ela", True)])


# ---------- _validate_image_method_switches ----------

def test_validate_image_method_switches_passes_when_at_least_one_true():
    orch._validate_image_method_switches({"ela": True, "exif": False})


def test_validate_image_method_switches_rejects_all_false():
    with pytest.raises(ValueError, match="At least one image detection method"):
        orch._validate_image_method_switches({"ela": False, "exif": False})


def test_validate_image_method_switches_none_is_ok():
    orch._validate_image_method_switches(None)


# ---------- _validate_image_uploads ----------

@override_settings(MEDIA_ROOT="/tmp/test-media-orch-validate")
def test_validate_image_uploads_returns_owned_uploads():
    user = make_user()
    task = make_detection_task(user=user)
    img1 = make_image_upload(detection_task=task)
    img2 = make_image_upload(detection_task=task)
    out = orch._validate_image_uploads(user, [img1.id, img2.id])
    assert {u.id for u in out} == {img1.id, img2.id}


def test_validate_image_uploads_rejects_empty_list():
    user = make_user()
    with pytest.raises(ValueError, match="No image IDs"):
        orch._validate_image_uploads(user, [])


def test_validate_image_uploads_rejects_non_list():
    user = make_user()
    with pytest.raises(ValueError, match="No image IDs"):
        orch._validate_image_uploads(user, None)


def test_validate_image_uploads_raises_when_none_found():
    user = make_user()
    with pytest.raises(FileNotFoundError, match="No valid images"):
        orch._validate_image_uploads(user, [999999])


# ---------- _reserve_detection_usage ----------

def test_reserve_detection_usage_non_llm_deducts_quota():
    org = make_organization(remaining_non_llm_uses=50)
    orch._reserve_detection_usage(org, if_use_llm=False, num_images=10)
    org.refresh_from_db()
    assert org.remaining_non_llm_uses == 40


def test_reserve_detection_usage_llm_deducts_quota():
    org = make_organization(remaining_llm_uses=5)
    orch._reserve_detection_usage(org, if_use_llm=True, num_images=2)
    org.refresh_from_db()
    assert org.remaining_llm_uses == 3


def test_reserve_detection_usage_rejects_missing_organization():
    with pytest.raises(ValueError, match="organization"):
        orch._reserve_detection_usage(None, if_use_llm=False, num_images=1)


def test_reserve_detection_usage_raises_when_non_llm_quota_insufficient():
    org = make_organization(remaining_non_llm_uses=5)
    with pytest.raises(ValueError, match="non-LLM"):
        orch._reserve_detection_usage(org, if_use_llm=False, num_images=10)


def test_reserve_detection_usage_raises_when_llm_quota_insufficient():
    org = make_organization(remaining_llm_uses=1)
    with pytest.raises(ValueError, match="LLM"):
        orch._reserve_detection_usage(org, if_use_llm=True, num_images=2)


def test_reserve_detection_usage_uses_database_balance_for_stale_instances():
    org = make_organization(remaining_non_llm_uses=1)
    stale_org = type(org).objects.get(pk=org.pk)

    orch._reserve_detection_usage(org, if_use_llm=False, num_images=1)
    with pytest.raises(ValueError, match="non-LLM"):
        orch._reserve_detection_usage(stale_org, if_use_llm=False, num_images=1)

    org.refresh_from_db()
    assert org.remaining_non_llm_uses == 0


# ---------- _refund_detection_usage ----------

def test_refund_detection_usage_no_op_when_org_none():
    orch._refund_detection_usage(None, if_use_llm=False, num_images=10)  # no exception


def test_refund_detection_usage_no_op_when_zero_images():
    org = make_organization(remaining_non_llm_uses=10)
    orch._refund_detection_usage(org, if_use_llm=False, num_images=0)
    org.refresh_from_db()
    assert org.remaining_non_llm_uses == 10


def test_refund_detection_usage_adds_back_to_correct_bucket():
    org = make_organization(remaining_non_llm_uses=10, remaining_llm_uses=1)
    orch._refund_detection_usage(org, if_use_llm=False, num_images=5)
    org.refresh_from_db()
    assert org.remaining_non_llm_uses == 15
    orch._refund_detection_usage(org, if_use_llm=True, num_images=2)
    org.refresh_from_db()
    assert org.remaining_llm_uses == 3


# ---------- _mark_detection_task_failed ----------

@override_settings(MEDIA_ROOT="/tmp/test-media-orch-fail")
def test_mark_detection_task_failed_updates_task_and_in_progress_results():
    task = make_detection_task(status="in_progress")
    img1 = make_image_upload(detection_task=task)
    img2 = make_image_upload(detection_task=task)
    DetectionResult.objects.create(image_upload=img1, detection_task=task, status="in_progress")
    DetectionResult.objects.create(image_upload=img2, detection_task=task, status="completed")

    orch._mark_detection_task_failed(task, "boom error")
    task.refresh_from_db()
    assert task.status == "failed"
    assert task.error_message == "boom error"
    assert task.completion_time is not None

    statuses = set(
        DetectionResult.objects.filter(detection_task=task).values_list("status", flat=True)
    )
    assert "failed" in statuses  # 进行中的转为 failed
    assert "completed" in statuses  # 已完成的保留


@override_settings(MEDIA_ROOT="/tmp/test-media-orch-fail")
def test_mark_detection_task_failed_truncates_long_error_message():
    task = make_detection_task(status="in_progress")
    long_msg = "x" * 3000
    orch._mark_detection_task_failed(task, long_msg)
    task.refresh_from_db()
    assert len(task.error_message) == 2000


# ---------- create_image_detection_task ----------

@override_settings(MEDIA_ROOT="/tmp/test-media-orch-create")
def test_create_image_detection_task_creates_task_and_results_and_reserves_quota():
    user = make_user()
    org = user.organization
    initial_quota = org.remaining_non_llm_uses
    task = make_detection_task(user=user)
    img1 = make_image_upload(detection_task=task)
    img2 = make_image_upload(detection_task=task)

    starter = MagicMock()
    commit_hook = lambda fn: fn()
    new_task, _ = orch.create_image_detection_task(
        user=user,
        image_ids=[img1.id, img2.id],
        if_use_llm=False,
        method_switches={"ela": True, "exif": False},
        on_commit=commit_hook,
        async_task_starter=starter,
    )

    assert new_task.status == "pending"
    assert new_task.if_use_llm is False
    assert DetectionResult.objects.filter(detection_task=new_task).count() == 2
    starter.assert_called_once()
    org.refresh_from_db()
    assert org.remaining_non_llm_uses == initial_quota - 2


@override_settings(MEDIA_ROOT="/tmp/test-media-orch-create")
def test_create_image_detection_task_mode_3_forces_llm_path():
    user = make_user()
    org = user.organization
    initial_llm_quota = org.remaining_llm_uses
    task = make_detection_task(user=user)
    img = make_image_upload(detection_task=task)
    starter = MagicMock()

    new_task, _ = orch.create_image_detection_task(
        user=user,
        image_ids=[img.id],
        mode=3,  # 强制走 LLM 路径
        if_use_llm=False,
        on_commit=lambda fn: fn(),
        async_task_starter=starter,
    )
    assert new_task.if_use_llm is True
    org.refresh_from_db()
    assert org.remaining_llm_uses == initial_llm_quota - 1


@override_settings(MEDIA_ROOT="/tmp/test-media-orch-create")
def test_create_image_detection_task_uses_default_task_name():
    user = make_user()
    task = make_detection_task(user=user)
    img = make_image_upload(detection_task=task)

    new_task, _ = orch.create_image_detection_task(
        user=user,
        image_ids=[img.id],
        task_name="",  # 空字符串触发默认名
        on_commit=lambda fn: fn(),
        async_task_starter=MagicMock(),
    )
    assert new_task.task_name == "New Detection Task"


@override_settings(MEDIA_ROOT="/tmp/test-media-orch-create")
def test_create_image_detection_task_attaches_unique_file_managements_to_resource_files():
    user = make_user()
    task = make_detection_task(user=user)
    img1 = make_image_upload(detection_task=task)
    img2 = make_image_upload(detection_task=task, file_management=img1.file_management)

    new_task, _ = orch.create_image_detection_task(
        user=user,
        image_ids=[img1.id, img2.id],
        on_commit=lambda fn: fn(),
        async_task_starter=MagicMock(),
    )
    # 两张图共享同一个 file_management，应去重
    assert new_task.resource_files.count() == 1


@override_settings(MEDIA_ROOT="/tmp/test-media-orch-create")
def test_create_image_detection_task_refunds_quota_when_creation_fails_after_reserve():
    user = make_user()
    org = user.organization
    initial_quota = org.remaining_non_llm_uses
    task = make_detection_task(user=user)
    img = make_image_upload(detection_task=task)

    def starter(*_args, **_kwargs):
        raise RuntimeError("submit failed")

    with pytest.raises(RuntimeError, match="submit failed"):
        orch.create_image_detection_task(
            user=user,
            image_ids=[img.id],
            on_commit=lambda fn: fn(),
            async_task_starter=starter,
        )

    org.refresh_from_db()
    assert org.remaining_non_llm_uses == initial_quota


# ---------- run_image_detection_task_async ----------

@override_settings(MEDIA_ROOT="/tmp/test-media-orch-async")
def test_run_image_detection_task_async_calls_executor():
    user = make_user()
    task = make_detection_task(user=user, status="pending")
    img = make_image_upload(detection_task=task)
    executor = MagicMock()
    orch.run_image_detection_task_async(
        task.id, [img.id], False, 1, detection_executor=executor,
    )
    executor.assert_called_once()
    kwargs = executor.call_args.kwargs
    assert kwargs["detection_task"].id == task.id


@override_settings(MEDIA_ROOT="/tmp/test-media-orch-async")
def test_run_image_detection_task_async_marks_failed_on_exception():
    user = make_user()
    org = user.organization
    org.remaining_non_llm_uses = 10
    org.save()
    task = make_detection_task(user=user, status="pending")
    img = make_image_upload(detection_task=task)

    executor = MagicMock(side_effect=RuntimeError("model crash"))
    orch.run_image_detection_task_async(
        task.id, [img.id], False, 1, detection_executor=executor,
    )

    task.refresh_from_db()
    assert task.status == "failed"
    assert "model crash" in task.error_message
    org.refresh_from_db()
    # 配额应被退还（1 张图）
    assert org.remaining_non_llm_uses == 11


@override_settings(MEDIA_ROOT="/tmp/test-media-orch-async")
def test_run_image_detection_task_async_no_images_marks_failed():
    user = make_user()
    task = make_detection_task(user=user, status="pending")
    executor = MagicMock()
    orch.run_image_detection_task_async(
        task.id, [999999], False, 1, detection_executor=executor,
    )
    task.refresh_from_db()
    assert task.status == "failed"
    executor.assert_not_called()


@override_settings(MEDIA_ROOT="/tmp/test-media-orch-async")
def test_run_image_detection_task_async_skips_non_pending_task():
    user = make_user()
    task = make_detection_task(user=user, status="completed")
    img = make_image_upload(detection_task=task)
    executor = MagicMock()

    orch.run_image_detection_task_async(
        task.id, [img.id], False, 1, detection_executor=executor,
    )

    task.refresh_from_db()
    assert task.status == "completed"
    executor.assert_not_called()
