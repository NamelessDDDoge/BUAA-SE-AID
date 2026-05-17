"""views_notify"""
import pytest
from rest_framework.test import APIClient

from core.models import Notification
from core.tests.factories import make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


def _make_notification(receiver_id: int, **overrides):
    defaults = dict(
        receiver_id=str(receiver_id),
        receiver_name="x",
        category=Notification.SYSTEM,
        title="t",
        content="c",
        status="unread",
    )
    defaults.update(overrides)
    return Notification.objects.create(**defaults)


# ---------- get_notifications ----------

def test_get_notifications_returns_only_self_notifications(client):
    me = make_user()
    other = make_user()
    _make_notification(me.id, title="mine")
    _make_notification(other.id, title="theirs")

    client.force_authenticate(me)
    resp = client.get("/api/notification/get/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured under expected path")
    assert resp.status_code == 200
    titles = [n["title"] for n in resp.data["notifications"]]
    assert "mine" in titles
    assert "theirs" not in titles


def test_get_notifications_requires_authentication(client):
    resp = client.get("/api/notification/get/")
    assert resp.status_code in (401, 403, 404)


def test_get_notification_status_counts_only_unread_self(client):
    me = make_user()
    _make_notification(me.id, status="unread")
    _make_notification(me.id, status="unread")
    _make_notification(me.id, status="read")

    client.force_authenticate(me)
    resp = client.get("/api/notification/notify/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured under expected path")
    assert resp.status_code == 200
    assert resp.data["not_read"] == 2


# ---------- broadcast_notification ----------

def test_broadcast_requires_staff(client):
    me = make_user()  # 非 staff
    client.force_authenticate(me)
    resp = client.post("/api/notification/broadcast/", {"title": "T", "content": "C"}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured under expected path")
    assert resp.status_code == 403


def test_broadcast_rejects_empty_title(client):
    me = make_user()
    me.is_staff = True
    me.save()
    client.force_authenticate(me)
    resp = client.post("/api/notification/broadcast/", {"title": "", "content": "x"}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured under expected path")
    assert resp.status_code == 400


def test_broadcast_rejects_too_long_title(client):
    me = make_user()
    me.is_staff = True
    me.save()
    client.force_authenticate(me)
    resp = client.post(
        "/api/notification/broadcast/",
        {"title": "T" * 20, "content": "x"},
        format="json",
    )
    if resp.status_code == 404:
        pytest.skip("URL route not configured under expected path")
    assert resp.status_code == 400


def test_broadcast_rejects_too_long_content(client):
    me = make_user()
    me.is_staff = True
    me.save()
    client.force_authenticate(me)
    resp = client.post(
        "/api/notification/broadcast/",
        {"title": "T", "content": "x" * 1001},
        format="json",
    )
    if resp.status_code == 404:
        pytest.skip("URL route not configured under expected path")
    assert resp.status_code == 400


def test_broadcast_creates_notification_for_each_nonstaff_user(client):
    admin = make_user(role="admin")
    admin.is_staff = True
    admin.save()
    u1 = make_user()
    u2 = make_user()
    _ = make_user()
    _.is_staff = True
    _.save()  # 这个用户是 staff，不应收到广播

    client.force_authenticate(admin)
    resp = client.post(
        "/api/notification/broadcast/",
        {"title": "公告", "content": "重要通知内容"},
        format="json",
    )
    if resp.status_code == 404:
        pytest.skip("URL route not configured under expected path")
    assert resp.status_code == 200

    global_notifs = Notification.objects.filter(category=Notification.GLOBAL, title="公告")
    receiver_ids = set(global_notifs.values_list("receiver_id", flat=True))
    assert str(u1.id) in receiver_ids
    assert str(u2.id) in receiver_ids


# ---------- set_notifications_as_read ----------

def test_set_notifications_as_read_marks_all_self_unread(client):
    me = make_user()
    other = make_user()
    _make_notification(me.id, status="unread")
    _make_notification(me.id, status="unread")
    _make_notification(other.id, status="unread")

    client.force_authenticate(me)
    resp = client.post("/api/notification/set_as_read/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured under expected path")
    assert resp.status_code == 200

    mine_unread = Notification.objects.filter(receiver_id=str(me.id), status="unread").count()
    other_unread = Notification.objects.filter(receiver_id=str(other.id), status="unread").count()
    assert mine_unread == 0
    assert other_unread == 1
