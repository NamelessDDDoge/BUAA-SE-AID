"""模型工厂入口。

手写工厂（不依赖 factory_boy），所有 model/integration 测试共用。
每个 make_* 返回一个已 .save() 的实例，参数可覆盖。
"""
from __future__ import annotations

import itertools
import uuid
from datetime import timedelta
from typing import Any, Optional

from django.utils import timezone


_counter = itertools.count(1)


def _seq() -> int:
    """每次调用递增，用于生成唯一字段值。"""
    return next(_counter)


def make_organization(**overrides: Any):
    from core.models import Organization
    n = _seq()
    defaults = dict(
        name=f"org-{n}-{uuid.uuid4().hex[:6]}",
        email=f"org-{n}-{uuid.uuid4().hex[:6]}@example.com",
        description=f"Org {n} description",
    )
    defaults.update(overrides)
    return Organization.objects.create(**defaults)


def make_user(*, organization=None, role: str = "publisher", **overrides: Any):
    from core.models import User
    n = _seq()
    org = organization if organization is not None else make_organization()
    defaults = dict(
        username=f"user-{n}-{uuid.uuid4().hex[:6]}",
        email=f"user-{n}-{uuid.uuid4().hex[:6]}@example.com",
        organization=org,
        role=role,
    )
    defaults.update(overrides)
    password = defaults.pop("password", "test-pass-1234")
    user = User(**defaults)
    user.set_password(password)
    user.save()
    return user


def make_invitation_code(*, organization=None, role: str = "publisher", **overrides: Any):
    from core.models import InvitationCode
    n = _seq()
    org = organization if organization is not None else make_organization()
    defaults = dict(
        code=f"{n:06d}"[-6:],
        organization=org,
        role=role,
        expires_at=timezone.now() + timedelta(days=7),
    )
    defaults.update(overrides)
    return InvitationCode.objects.create(**defaults)


def make_file_management(*, user=None, organization=None, **overrides: Any):
    from core.models import FileManagement
    if user is None:
        user = make_user(organization=organization)
    n = _seq()
    defaults = dict(
        user=user,
        organization=user.organization,
        file_name=f"file-{n}.png",
        file_size=1024 * n,
        file_type="image/png",
        resource_type="image",
    )
    defaults.update(overrides)
    return FileManagement.objects.create(**defaults)


def make_detection_task(*, user=None, organization=None, task_type: str = "image", **overrides: Any):
    from core.models import DetectionTask
    if user is None:
        user = make_user(organization=organization)
    n = _seq()
    defaults = dict(
        user=user,
        organization=user.organization,
        task_name=f"task-{n}",
        task_type=task_type,
        status="pending",
    )
    defaults.update(overrides)
    return DetectionTask.objects.create(**defaults)


def make_image_upload(*, detection_task=None, file_management=None, **overrides: Any):
    """ImageUpload 需要真实图片文件 — 由 fixtures/images.py 的 build_test_image 提供。"""
    from core.models import ImageUpload
    from core.tests.fixtures.images import build_test_image

    if detection_task is None:
        detection_task = make_detection_task()
    if file_management is None:
        file_management = make_file_management(user=detection_task.user)
    defaults = dict(
        detection_task=detection_task,
        file_management=file_management,
        image=build_test_image(),
    )
    defaults.update(overrides)
    return ImageUpload.objects.create(**defaults)


def make_detection_result(*, image_upload=None, detection_task=None, **overrides: Any):
    from core.models import DetectionResult
    if image_upload is None:
        if detection_task is None:
            detection_task = make_detection_task()
        image_upload = make_image_upload(detection_task=detection_task)
    defaults = dict(
        image_upload=image_upload,
        detection_task=detection_task if detection_task is not None else image_upload.detection_task,
        status="in_progress",
    )
    defaults.update(overrides)
    return DetectionResult.objects.create(**defaults)


def make_review_request(*, user=None, detection_result=None, **overrides: Any):
    from core.models import ReviewRequest
    if detection_result is None:
        detection_result = make_detection_result()
    if user is None:
        user = detection_result.detection_task.user
    defaults = dict(
        detection_result=detection_result,
        user=user,
        organization=user.organization,
        reason="申请人工复核",
        check_reason="",
    )
    defaults.update(overrides)
    return ReviewRequest.objects.create(**defaults)


def make_manual_review(*, review_request=None, reviewer=None, **overrides: Any):
    from core.models import ManualReview
    if review_request is None:
        review_request = make_review_request()
    if reviewer is None:
        reviewer = make_user(organization=review_request.organization, role="reviewer")
    defaults = dict(
        review_request=review_request,
        reviewer=reviewer,
        organization=review_request.organization,
    )
    defaults.update(overrides)
    return ManualReview.objects.create(**defaults)


def make_llm_model(**overrides: Any):
    from core.models import LLMModel
    n = _seq()
    defaults = dict(
        model_name=f"llm-{n}-{uuid.uuid4().hex[:6]}",
        display_name=f"LLM {n}",
        provider="openai_compat",
        model_type="chat",
        endpoint="https://example.com/v1",
        api_key="sk-test-key",
        is_active=True,
    )
    defaults.update(overrides)
    return LLMModel.objects.create(**defaults)
