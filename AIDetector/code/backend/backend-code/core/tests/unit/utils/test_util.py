"""core/util.py — send_notification + send_ai_detection_complete_notification"""
import pytest

from core.models import Notification
from core.tests.factories import make_detection_task, make_user
from core.util import (
    send_ai_detection_complete_notification,
    send_notification,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_send_notification_creates_unread_record():
    send_notification(
        receiver_id="42",
        receiver_name="bob",
        sender_id="7",
        sender_name="alice",
        category=Notification.P2R,
        title="t",
        content="c",
        url="/foo",
    )
    n = Notification.objects.get()
    assert n.receiver_id == "42"
    assert n.receiver_name == "bob"
    assert n.sender_id == "7"
    assert n.sender_name == "alice"
    assert n.category == Notification.P2R
    assert n.title == "t"
    assert n.content == "c"
    assert n.url == "/foo"
    assert n.status == "unread"
    assert n.notified_at is not None


def test_send_notification_optional_sender_and_url():
    send_notification(
        receiver_id="1", receiver_name="r",
        category=Notification.SYSTEM, title="t", content="c",
    )
    n = Notification.objects.get()
    assert n.sender_id is None
    assert n.sender_name is None
    assert n.url is None


def test_send_ai_detection_complete_notification_uses_system_category():
    user = make_user()
    task = make_detection_task(user=user)
    send_ai_detection_complete_notification(user.id, user.username, task)

    n = Notification.objects.get()
    assert n.category == Notification.SYSTEM
    assert n.title == "AI检测已完成"
    assert n.url == f"/step/{task.id}"
    assert n.receiver_id == str(user.id)
