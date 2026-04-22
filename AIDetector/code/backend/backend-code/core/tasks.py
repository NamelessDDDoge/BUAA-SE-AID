from .models import DetectionTask
from .services.orchestrators import run_paper_detection_task, run_review_detection_task
from .utils.report_generator import generate_task_report


def generate_report_for_task(task_id):
    task = DetectionTask.objects.get(id=task_id)
    return generate_task_report(task)


def run_paper_detection(task_id, api_key=None):
    # Compatibility wrapper kept for tests and any legacy imports.
    return run_paper_detection_task(task_id, api_key=api_key)


def run_review_detection(task_id, api_key=None):
    # Compatibility wrapper kept for tests and any legacy imports.
    return run_review_detection_task(task_id, api_key=api_key)
