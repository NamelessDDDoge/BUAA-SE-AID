"""5.17 Log 表"""
import pytest

from core.models import Log
from core.tests.factories import make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_str_contains_username_operation_and_time():
    user = make_user(username="grace")
    log = Log.objects.create(
        user=user, operation_type="upload", related_model="ImageUpload", related_id=42,
    )
    rendered = str(log)
    assert "grace" in rendered
    assert "upload" in rendered


def test_operation_time_defaulted():
    user = make_user()
    log = Log.objects.create(
        user=user, operation_type="detection", related_model="DetectionTask", related_id=1,
    )
    assert log.operation_time is not None


def test_all_operation_types_accepted():
    user = make_user()
    for op in ("upload", "detection", "review_request", "manual_review"):
        log = Log.objects.create(
            user=user, operation_type=op, related_model="X", related_id=1,
        )
        assert log.operation_type == op
