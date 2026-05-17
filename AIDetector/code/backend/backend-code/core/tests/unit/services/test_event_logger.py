"""services/event_logger.py"""
import pytest

from core.models import Log
from core.services.event_logger import log_user_event
from core.tests.factories import make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_log_user_event_creates_log_row():
    user = make_user()
    log = log_user_event(
        user=user, operation_type="upload", related_model="ImageUpload", related_id=42,
    )
    assert Log.objects.count() == 1
    assert log.user_id == user.id
    assert log.operation_type == "upload"
    assert log.related_model == "ImageUpload"
    assert log.related_id == 42


def test_log_user_event_returns_persisted_instance():
    user = make_user()
    log = log_user_event(
        user=user, operation_type="detection", related_model="DetectionTask", related_id=7,
    )
    log.refresh_from_db()
    assert log.operation_time is not None
