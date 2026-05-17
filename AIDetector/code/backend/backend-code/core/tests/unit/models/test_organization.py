"""5.2 Organization 表"""
import pytest
from django.db import IntegrityError

from core.models import Organization
from core.tests.factories import make_organization

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_organization_str_returns_name():
    org = make_organization(name="北航软院")
    assert str(org) == "北航软院"


def test_organization_default_quotas_are_100_and_3():
    org = make_organization()
    assert org.remaining_non_llm_uses == 100
    assert org.remaining_llm_uses == 3
    assert org.last_reset_time is None


def test_organization_name_must_be_unique():
    make_organization(name="duplicate-name")
    with pytest.raises(IntegrityError):
        Organization.objects.create(name="duplicate-name", email="other@example.com")


def test_organization_email_must_be_unique():
    make_organization(email="dup@example.com")
    with pytest.raises(IntegrityError):
        Organization.objects.create(name="other-org", email="dup@example.com")


def test_can_use_non_llm_returns_true_when_quota_sufficient():
    org = make_organization()
    assert org.can_use_non_llm(50) is True
    assert org.can_use_non_llm(100) is True


def test_can_use_non_llm_returns_false_when_quota_exceeded():
    org = make_organization(remaining_non_llm_uses=10)
    assert org.can_use_non_llm(11) is False


def test_can_use_llm_returns_true_when_quota_sufficient():
    org = make_organization()
    assert org.can_use_llm(1) is True
    assert org.can_use_llm(3) is True


def test_can_use_llm_returns_false_when_quota_exceeded():
    org = make_organization(remaining_llm_uses=2)
    assert org.can_use_llm(3) is False


def test_decrement_non_llm_uses_reduces_balance_when_sufficient():
    org = make_organization(remaining_non_llm_uses=50)
    org.decrement_non_llm_uses(20)
    org.refresh_from_db()
    assert org.remaining_non_llm_uses == 30


def test_decrement_non_llm_uses_is_no_op_when_insufficient():
    org = make_organization(remaining_non_llm_uses=5)
    org.decrement_non_llm_uses(10)
    org.refresh_from_db()
    assert org.remaining_non_llm_uses == 5


def test_decrement_llm_uses_reduces_balance_when_sufficient():
    org = make_organization(remaining_llm_uses=3)
    org.decrement_llm_uses(1)
    org.refresh_from_db()
    assert org.remaining_llm_uses == 2


def test_add_non_llm_uses_increases_balance():
    org = make_organization(remaining_non_llm_uses=10)
    org.add_non_llm_uses(50)
    org.refresh_from_db()
    assert org.remaining_non_llm_uses == 60


def test_add_llm_uses_increases_balance():
    org = make_organization(remaining_llm_uses=0)
    org.add_llm_uses(5)
    org.refresh_from_db()
    assert org.remaining_llm_uses == 5


def test_get_remaining_uses_returns_dict_with_three_keys():
    org = make_organization()
    info = org.get_remaining_uses()
    assert set(info.keys()) == {"remaining_non_llm_uses", "remaining_llm_uses", "reset_time"}
    assert info["remaining_non_llm_uses"] == 100
    assert info["remaining_llm_uses"] == 3
    assert info["reset_time"] is None
