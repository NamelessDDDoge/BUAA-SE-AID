"""5.5 PublisherReviewerRelationship 表"""
import pytest
from django.db import IntegrityError

from core.models import PublisherReviewerRelationship
from core.tests.factories import make_organization, make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_relationship_defaults_active():
    org = make_organization()
    pub = make_user(organization=org, role="publisher")
    rev = make_user(organization=org, role="reviewer")
    rel = PublisherReviewerRelationship.objects.create(publisher=pub, reviewer=rev)
    assert rel.is_active is True
    assert rel.created_at is not None


def test_publisher_reviewer_pair_must_be_unique():
    org = make_organization()
    pub = make_user(organization=org, role="publisher")
    rev = make_user(organization=org, role="reviewer")
    PublisherReviewerRelationship.objects.create(publisher=pub, reviewer=rev)
    with pytest.raises(IntegrityError):
        PublisherReviewerRelationship.objects.create(publisher=pub, reviewer=rev)


def test_same_publisher_can_have_multiple_reviewers():
    org = make_organization()
    pub = make_user(organization=org, role="publisher")
    rev1 = make_user(organization=org, role="reviewer")
    rev2 = make_user(organization=org, role="reviewer")
    PublisherReviewerRelationship.objects.create(publisher=pub, reviewer=rev1)
    PublisherReviewerRelationship.objects.create(publisher=pub, reviewer=rev2)
    assert pub.publisher_relationships.count() == 2


def test_same_reviewer_can_serve_multiple_publishers():
    org = make_organization()
    pub1 = make_user(organization=org, role="publisher")
    pub2 = make_user(organization=org, role="publisher")
    rev = make_user(organization=org, role="reviewer")
    PublisherReviewerRelationship.objects.create(publisher=pub1, reviewer=rev)
    PublisherReviewerRelationship.objects.create(publisher=pub2, reviewer=rev)
    assert rev.reviewer_relationships.count() == 2
