"""5.15 ImageReview 表"""
import pytest
from django.test import override_settings

from core.models import ImageReview
from core.tests.factories import make_image_upload, make_manual_review

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _build_image_review(**overrides):
    mr = overrides.pop("manual_review", None) or make_manual_review()
    img = overrides.pop("img", None) or make_image_upload(
        detection_task=mr.review_request.detection_result.detection_task
    )
    defaults = dict(manual_review=mr, img=img)
    defaults.update(overrides)
    return ImageReview.objects.create(**defaults)


@override_settings(MEDIA_ROOT="/tmp/test-media-image-review")
def test_all_seven_scores_and_reasons_and_points_default_null():
    ir = _build_image_review()
    for i in range(1, 8):
        assert getattr(ir, f"score{i}") is None
        assert getattr(ir, f"reason{i}") is None
        assert getattr(ir, f"points{i}") is None


@override_settings(MEDIA_ROOT="/tmp/test-media-image-review")
def test_result_defaults_null_and_can_be_set_true_false():
    ir = _build_image_review()
    assert ir.result is None
    ir.result = True
    ir.save()
    ir.refresh_from_db()
    assert ir.result is True


@override_settings(MEDIA_ROOT="/tmp/test-media-image-review")
def test_scores_can_be_persisted_for_each_method():
    ir = _build_image_review(
        score1=80, score2=75, score3=90, score4=60, score5=85, score6=70, score7=95,
    )
    ir.refresh_from_db()
    assert ir.score1 == 80
    assert ir.score7 == 95


@override_settings(MEDIA_ROOT="/tmp/test-media-image-review")
def test_points_json_round_trip():
    points = [[1, 2], [3, 4], [5, 6]]
    ir = _build_image_review(points1=points, points7=points)
    ir.refresh_from_db()
    assert ir.points1 == points
    assert ir.points7 == points


@override_settings(MEDIA_ROOT="/tmp/test-media-image-review")
def test_reasons_text_round_trip():
    ir = _build_image_review(reason1="拼接痕迹明显", reason3="对比度异常")
    ir.refresh_from_db()
    assert ir.reason1 == "拼接痕迹明显"
    assert ir.reason3 == "对比度异常"
