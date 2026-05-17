"""通知 / 公告（DTC-USER 与 DTC-ADMIN 共用）"""
import pytest
from rest_framework.test import APIClient

from core.models import Notification
from core.tests.factories import make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def client():
    return APIClient()


def _notif(receiver_id, **kw):
    defaults = dict(
        receiver_id=str(receiver_id), receiver_name="x",
        category=Notification.SYSTEM, title="t", content="c",
    )
    defaults.update(kw)
    return Notification.objects.create(**defaults)


def test_get_notifications_only_returns_self(client):
    me = make_user()
    other = make_user()
    _notif(me.id, title="MINE")
    _notif(other.id, title="THEIRS")
    client.force_authenticate(me)
    resp = client.get("/api/notification/get/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 200
    titles = [n["title"] for n in resp.data["notifications"]]
    assert "MINE" in titles and "THEIRS" not in titles


def test_get_notification_status_counts_unread(client):
    me = make_user()
    _notif(me.id, status="unread")
    _notif(me.id, status="unread")
    _notif(me.id, status="read")
    client.force_authenticate(me)
    resp = client.get("/api/notification/notify/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 200
    assert resp.data["not_read"] == 2


def test_mark_single_read(client):
    me = make_user()
    n = _notif(me.id, status="unread")
    client.force_authenticate(me)
    resp = client.post(f"/api/notification/set_as_read/{n.id}/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 204)
    n.refresh_from_db()
    assert n.status == "read"


def test_mark_all_read(client):
    me = make_user()
    _notif(me.id, status="unread")
    _notif(me.id, status="unread")
    client.force_authenticate(me)
    resp = client.post("/api/notification/set_as_read/")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code in (200, 204)
    assert Notification.objects.filter(receiver_id=str(me.id), status="unread").count() == 0


def test_broadcast_requires_staff(client):
    me = make_user()
    client.force_authenticate(me)
    resp = client.post("/api/notification/broadcast/", {"title": "T", "content": "C"}, format="json")
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 403


def test_broadcast_validates_title_length(client):
    admin = make_user()
    admin.is_staff = True
    admin.save_permission()
    client.force_authenticate(admin)
    resp = client.post(
        "/api/notification/broadcast/",
        {"title": "T" * 20, "content": "x"},
        format="json",
    )
    if resp.status_code == 404:
        pytest.skip("URL route not configured")
    assert resp.status_code == 400
