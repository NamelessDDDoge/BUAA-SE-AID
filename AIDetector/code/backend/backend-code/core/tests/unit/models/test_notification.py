"""5.18 Notification 表"""
import time

import pytest

from core.models import Notification

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _make(**overrides):
    defaults = dict(
        receiver_id="r-1",
        receiver_name="receiver",
        category=Notification.SYSTEM,
        title="t",
        content="c",
    )
    defaults.update(overrides)
    return Notification.objects.create(**defaults)


def test_category_constants_match_design_doc():
    assert Notification.GLOBAL == 1
    assert Notification.SYSTEM == 2
    assert Notification.P2R == 3
    assert Notification.R2P == 4


def test_default_status_is_unread():
    n = _make()
    assert n.status == "unread"


def test_can_mark_status_read():
    n = _make()
    n.status = "read"
    n.save()
    n.refresh_from_db()
    assert n.status == "read"


def test_str_contains_category_display_and_title():
    n = _make(title="重要通告", category=Notification.GLOBAL)
    rendered = str(n)
    assert "重要通告" in rendered
    assert "GLOBAL" in rendered


def test_ordering_is_descending_by_notified_at():
    n1 = _make(title="older")
    time.sleep(0.01)
    n2 = _make(title="newer")
    titles = list(Notification.objects.values_list("title", flat=True))
    assert titles[0] == "newer"
    assert titles[1] == "older"


def test_sender_fields_optional():
    n = _make()
    assert n.sender_id is None
    assert n.sender_name is None


def test_url_field_optional():
    n = _make(url="/admin/foo")
    assert n.url == "/admin/foo"


def test_db_table_name_is_notification():
    assert Notification._meta.db_table == "notification"
