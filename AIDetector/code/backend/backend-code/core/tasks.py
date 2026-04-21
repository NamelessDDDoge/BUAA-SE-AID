import os

from celery import shared_task

from .models import DetectionTask
from .services.orchestrators import run_paper_detection_task, run_review_detection_task
from .utils.report_generator import generate_detection_task_report


@shared_task
def generate_report_for_task(task_id):
    task = DetectionTask.objects.get(id=task_id)
    return generate_detection_task_report(task)


@shared_task
def run_paper_detection(task_id, api_key=None):
    return run_paper_detection_task(task_id, api_key=api_key)


@shared_task
def run_review_detection(task_id, api_key=None):
    return run_review_detection_task(task_id, api_key=api_key)
