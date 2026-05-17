"""5.16 Feedback 表"""
import pytest
from django.test import override_settings

from core.models import Feedback
from core.tests.factories import make_manual_review, make_user

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@override_settings(MEDIA_ROOT="/tmp/test-media-feedback")
def test_is_like_defaults_false():
    mr = make_manual_review()
    fb = Feedback.objects.create(manual_review=mr, user=mr.review_request.user)
    assert fb.is_like is False


@override_settings(MEDIA_ROOT="/tmp/test-media-feedback")
def test_str_includes_username_and_review_id():
    user = make_user(username="frank")
    mr = make_manual_review()
    fb = Feedback.objects.create(manual_review=mr, user=user, is_like=True, comment="nice")
    rendered = str(fb)
    assert "frank" in rendered
    assert str(mr.id) in rendered


@override_settings(MEDIA_ROOT="/tmp/test-media-feedback")
def test_comment_can_be_blank():
    mr = make_manual_review()
    fb = Feedback.objects.create(manual_review=mr, user=mr.review_request.user)
    assert fb.comment is None or fb.comment == ""


@override_settings(MEDIA_ROOT="/tmp/test-media-feedback")
def test_feedback_time_defaulted():
    mr = make_manual_review()
    fb = Feedback.objects.create(manual_review=mr, user=mr.review_request.user)
    assert fb.feedback_time is not None
