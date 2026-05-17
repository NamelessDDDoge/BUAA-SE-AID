"""5.1 OrganizationApplication 表"""
import pytest

from core.models import OrganizationApplication
from core.tests.factories import make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _make_application(**overrides):
    defaults = dict(
        name="申请组织 A",
        email="apply@example.com",
        admin_username="apply-admin",
        admin_email="apply-admin@example.com",
        admin_password="hashed-password",
    )
    defaults.update(overrides)
    return OrganizationApplication.objects.create(**defaults)


def test_status_defaults_to_pending():
    app = _make_application()
    assert app.status == "pending"


def test_status_accepts_approved_and_rejected():
    for status in ("approved", "rejected"):
        app = _make_application(status=status)
        assert app.status == status


def test_str_includes_name_and_status():
    app = _make_application(name="北航", status="approved")
    rendered = str(app)
    assert "北航" in rendered
    assert "approved" in rendered


def test_submitted_at_defaulted_on_save():
    app = _make_application()
    assert app.submitted_at is not None


def test_reviewer_can_be_attached_after_handling():
    app = _make_application()
    admin = make_user(role="admin")
    app.reviewer = admin
    app.save()
    app.refresh_from_db()
    assert app.reviewer_id == admin.id
