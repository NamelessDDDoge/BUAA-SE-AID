"""5.3/5.4 InvitationCode + User 表"""
from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from core.models import InvitationCode, User
from core.tests.factories import make_invitation_code, make_organization, make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# ---------- User ----------

def test_user_str_returns_username():
    user = make_user(username="alice")
    assert str(user) == "alice"


def test_user_email_must_be_unique():
    make_user(email="dup@example.com")
    with pytest.raises(IntegrityError):
        u = User(username="other-u", email="dup@example.com", organization=make_organization())
        u.set_password("x")
        u.save()


def test_save_sets_publisher_permission_to_1110():
    user = make_user(role="publisher")
    assert user.permission == 1110


def test_save_sets_reviewer_permission_to_1():
    user = make_user(role="reviewer")
    assert user.permission == 1


def test_save_sets_admin_permission_to_none():
    user = make_user(role="admin")
    assert user.permission is None


def test_has_permission_publisher_can_upload_submit_publish_but_not_review():
    user = make_user(role="publisher")
    assert user.has_permission("upload") is True
    assert user.has_permission("submit") is True
    assert user.has_permission("publish") is True
    assert user.has_permission("review") is False


def test_has_permission_reviewer_can_only_review():
    user = make_user(role="reviewer")
    assert user.has_permission("upload") is False
    assert user.has_permission("submit") is False
    assert user.has_permission("publish") is False
    assert user.has_permission("review") is True


def test_has_permission_returns_false_when_user_lacks_organization():
    user = make_user(role="publisher")
    user.organization = None
    user.save_permission()
    assert user.has_permission("upload") is False


def test_has_permission_unknown_perm_type_returns_false():
    user = make_user(role="publisher")
    assert user.has_permission("delete-everything") is False


def test_set_reset_code_generates_6_digit_code_with_expiry():
    user = make_user()
    user.set_reset_code()
    user.refresh_from_db()
    assert user.reset_code is not None
    assert len(user.reset_code) == 6
    assert user.reset_code.isdigit()
    assert user.reset_code_expiry is not None
    assert user.reset_code_expiry > timezone.now()


def test_is_reset_code_valid_true_when_code_not_expired():
    user = make_user()
    user.reset_code = "123456"
    user.reset_code_expiry = timezone.now() + timedelta(minutes=5)
    user.save()
    assert user.is_reset_code_valid() is True


def test_is_reset_code_valid_false_when_expired():
    user = make_user()
    user.reset_code = "123456"
    user.reset_code_expiry = timezone.now() - timedelta(minutes=1)
    user.save()
    assert user.is_reset_code_valid() is False


def test_user_default_quotas_are_100_and_3():
    user = make_user()
    assert user.remaining_non_llm_uses == 100
    assert user.remaining_llm_uses == 3


def test_can_use_non_llm_returns_true_when_quota_sufficient():
    user = make_user()
    assert user.can_use_non_llm(50) is True


def test_decrement_llm_uses_no_op_when_insufficient():
    user = make_user(remaining_llm_uses=1)
    user.decrement_llm_uses(2)
    user.refresh_from_db()
    assert user.remaining_llm_uses == 1


# ---------- InvitationCode ----------

def test_invitation_code_is_unique():
    make_invitation_code(code="ABC123")
    with pytest.raises(IntegrityError):
        InvitationCode.objects.create(
            code="ABC123",
            organization=make_organization(),
            role="publisher",
            expires_at=timezone.now() + timedelta(days=1),
        )


def test_invitation_code_defaults_unused():
    code = make_invitation_code()
    assert code.is_used is False


def test_invitation_code_str_contains_org_name_and_role():
    org = make_organization(name="test-org-xyz")
    code = make_invitation_code(organization=org, role="reviewer")
    rendered = str(code)
    assert "test-org-xyz" in rendered
    assert "reviewer" in rendered


def test_invitation_code_role_must_be_publisher_or_reviewer():
    # CharField with choices: 值层面不会阻止任意字符串，但 full_clean 会
    code = make_invitation_code(role="publisher")
    code.full_clean()  # should not raise
    code.role = "intruder"
    with pytest.raises(Exception):
        code.full_clean()
