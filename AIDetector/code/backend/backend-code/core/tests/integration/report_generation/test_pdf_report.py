"""Integration coverage for task PDF report generation."""
import os

import fitz
import pytest

from core.models import DetectionResult
from core.tests.factories import make_detection_task, make_image_upload
from core.utils.report_generator import ensure_task_report_file

pytestmark = [pytest.mark.integration, pytest.mark.report, pytest.mark.django_db]


def _pdf_text(abs_path):
    with fitz.open(abs_path) as pdf:
        return "".join(page.get_text() for page in pdf)


def test_completed_image_task_generates_downloadable_pdf_report(settings, isolated_media):
    task = make_detection_task(task_type="image", status="completed")
    image_upload = make_image_upload(detection_task=task)
    DetectionResult.objects.create(
        detection_task=task,
        image_upload=image_upload,
        status="completed",
        is_fake=True,
        confidence_score=0.91,
    )

    report_name = ensure_task_report_file(task, force=True)

    abs_path = os.path.join(settings.MEDIA_ROOT, report_name)
    assert os.path.exists(abs_path)
    assert report_name == f"reports/task_{task.id}_report.pdf"
    assert "Image Forensic Report" in _pdf_text(abs_path)


def test_report_generation_dispatches_by_task_type(settings, isolated_media):
    task = make_detection_task(
        task_type="paper",
        status="completed",
        text_detection_results={
            "document": {"file_name": "paper.pdf", "segment_count": 1},
            "paragraph_results": [],
            "suspicious_paragraphs": [],
            "confirmed_ai_paragraphs": [],
            "reference_results": [],
            "data_authenticity_results": {"summary": "-", "findings": []},
            "overall_evaluation": {"risk_level": "low", "summary": "No high risk evidence."},
            "image_results": [],
        },
    )

    report_name = ensure_task_report_file(task, force=True)

    abs_path = os.path.join(settings.MEDIA_ROOT, report_name)
    assert os.path.exists(abs_path)
    text = _pdf_text(abs_path)
    assert "Paper Detection Report" in text
    assert "Image Forensic Report" not in text
