"""PaperDetectionResult / PaperParagraphResult / PaperReferenceResult

代码里实际存在但《概要设计》5.x 列表未列出的模型。
对应论文检测（DTC-USER-3 论文链路）的结果存储。
"""
import pytest
from django.db import IntegrityError

from core.models import (
    PaperDetectionResult,
    PaperParagraphResult,
    PaperReferenceResult,
)
from core.tests.factories import make_detection_task, make_file_management

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _make_paper_result(**overrides):
    task = overrides.pop("detection_task", None) or make_detection_task(task_type="paper")
    defaults = dict(detection_task=task)
    defaults.update(overrides)
    return PaperDetectionResult.objects.create(**defaults)


# ---------- PaperDetectionResult ----------

def test_paper_detection_result_one_to_one_with_task():
    task = make_detection_task(task_type="paper")
    _make_paper_result(detection_task=task)
    with pytest.raises(IntegrityError):
        PaperDetectionResult.objects.create(detection_task=task)


def test_paper_detection_result_default_counts_are_zero():
    pr = _make_paper_result()
    assert pr.paragraph_count == 0
    assert pr.segment_count == 0
    assert pr.reference_count == 0
    assert pr.image_detection_enabled is True


def test_paper_detection_result_str_includes_task_id():
    pr = _make_paper_result()
    assert str(pr.detection_task.id) in str(pr)


def test_source_file_set_null_when_file_deleted():
    f = make_file_management(resource_type="paper")
    task = make_detection_task(task_type="paper", user=f.user)
    pr = PaperDetectionResult.objects.create(detection_task=task, source_file=f)
    f.delete()
    pr.refresh_from_db()
    assert pr.source_file is None


# ---------- PaperParagraphResult ----------

def test_paper_paragraph_unique_index_within_result():
    pr = _make_paper_result()
    PaperParagraphResult.objects.create(paper_detection_result=pr, paragraph_index=0)
    with pytest.raises(IntegrityError):
        PaperParagraphResult.objects.create(paper_detection_result=pr, paragraph_index=0)


def test_paper_paragraph_ordering_by_index():
    pr = _make_paper_result()
    PaperParagraphResult.objects.create(paper_detection_result=pr, paragraph_index=2, text="c")
    PaperParagraphResult.objects.create(paper_detection_result=pr, paragraph_index=0, text="a")
    PaperParagraphResult.objects.create(paper_detection_result=pr, paragraph_index=1, text="b")
    texts = list(pr.paragraph_results.values_list("text", flat=True))
    assert texts == ["a", "b", "c"]


def test_paper_paragraph_default_probability_is_zero():
    pr = _make_paper_result()
    para = PaperParagraphResult.objects.create(paper_detection_result=pr, paragraph_index=0)
    assert para.probability == 0.0
    assert para.label == ""


# ---------- PaperReferenceResult ----------

def test_paper_reference_unique_index_within_result():
    pr = _make_paper_result()
    PaperReferenceResult.objects.create(paper_detection_result=pr, reference_index=0)
    with pytest.raises(IntegrityError):
        PaperReferenceResult.objects.create(paper_detection_result=pr, reference_index=0)


def test_paper_reference_default_exists_and_relevant_false():
    pr = _make_paper_result()
    ref = PaperReferenceResult.objects.create(paper_detection_result=pr, reference_index=0)
    assert ref.exists is False
    assert ref.is_relevant is False
    assert ref.overlap_terms == []


def test_paper_reference_overlap_terms_json_round_trip():
    pr = _make_paper_result()
    ref = PaperReferenceResult.objects.create(
        paper_detection_result=pr, reference_index=0, overlap_terms=["term1", "term2"],
    )
    ref.refresh_from_db()
    assert ref.overlap_terms == ["term1", "term2"]
