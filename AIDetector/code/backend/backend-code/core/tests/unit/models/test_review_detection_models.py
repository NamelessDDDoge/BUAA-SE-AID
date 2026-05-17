"""ReviewDetectionResult / ReviewParagraphResult

代码里实际存在但《概要设计》5.x 列表未列出的模型。
对应同行评审检测（DTC-USER-3 同行评审链路）的结果存储。
"""
import pytest
from django.db import IntegrityError

from core.models import ReviewDetectionResult, ReviewParagraphResult
from core.tests.factories import make_detection_task

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _make_result(**overrides):
    task = overrides.pop("detection_task", None) or make_detection_task(task_type="review")
    defaults = dict(detection_task=task)
    defaults.update(overrides)
    return ReviewDetectionResult.objects.create(**defaults)


def test_one_to_one_with_task():
    task = make_detection_task(task_type="review")
    _make_result(detection_task=task)
    with pytest.raises(IntegrityError):
        ReviewDetectionResult.objects.create(detection_task=task)


def test_default_segment_counts_are_zero():
    rr = _make_result()
    assert rr.paper_segment_count == 0
    assert rr.review_segment_count == 0


def test_str_includes_task_id():
    rr = _make_result()
    assert str(rr.detection_task.id) in str(rr)


def test_paragraph_index_unique_per_result():
    rr = _make_result()
    ReviewParagraphResult.objects.create(review_detection_result=rr, paragraph_index=0)
    with pytest.raises(IntegrityError):
        ReviewParagraphResult.objects.create(review_detection_result=rr, paragraph_index=0)


def test_paragraph_ordering_by_index():
    rr = _make_result()
    ReviewParagraphResult.objects.create(review_detection_result=rr, paragraph_index=2)
    ReviewParagraphResult.objects.create(review_detection_result=rr, paragraph_index=0)
    ReviewParagraphResult.objects.create(review_detection_result=rr, paragraph_index=1)
    indices = list(rr.paragraph_results.values_list("paragraph_index", flat=True))
    assert indices == [0, 1, 2]


def test_paragraph_relevance_fields_optional():
    rr = _make_result()
    para = ReviewParagraphResult.objects.create(
        review_detection_result=rr,
        paragraph_index=0,
        relevance_score=0.78,
        relevance_label="related",
        paper_paragraph_index=3,
    )
    para.refresh_from_db()
    assert para.relevance_score == pytest.approx(0.78)
    assert para.relevance_label == "related"
    assert para.paper_paragraph_index == 3
