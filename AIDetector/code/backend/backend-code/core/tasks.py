import os

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import DetectionTask
from .utils.report_generator import generate_detection_task_report


@shared_task
def generate_report_for_task(task_id):
    task = DetectionTask.objects.get(id=task_id)
    return generate_detection_task_report(task)


@shared_task
def run_paper_detection(task_id, api_key=None):
    import requests

    task = DetectionTask.objects.get(id=task_id)
    task.status = "in_progress"
    task.save(update_fields=["status"])

    file_management = task.resource_files.first()
    if not file_management:
        task.status = "completed"
        task.save(update_fields=["status"])
        return "No file found"

    file_path = os.path.join(settings.MEDIA_ROOT, file_management.stored_path)
    if not os.path.exists(file_path):
        task.status = "completed"
        task.save(update_fields=["status"])
        return "File path does not exist"

    text_content = ""
    try:
        ext = file_path.lower().split(".")[-1]
        if ext == "pdf":
            import fitz

            with fitz.open(file_path) as document:
                text_content = "".join(page.get_text() for page in document)
        elif ext == "docx":
            import docx

            document = docx.Document(file_path)
            text_content = "\n".join(paragraph.text for paragraph in document.paragraphs)
        else:
            with open(file_path, "r", encoding="utf-8") as handle:
                text_content = handle.read()
    except Exception:
        try:
            with open(file_path, "r", encoding="gbk") as handle:
                text_content = handle.read()
        except Exception:
            text_content = "无法读取文件内容，请上传可解析的文本文件。"

    paragraphs = [paragraph.strip() for paragraph in text_content.split("\n") if paragraph.strip()]
    segments = []
    current_segment = ""
    for paragraph in paragraphs:
        if len(current_segment) + len(paragraph) < 500:
            current_segment += paragraph + " "
        else:
            if current_segment:
                segments.append(current_segment.strip())
            current_segment = paragraph + " "
    if current_segment:
        segments.append(current_segment.strip())

    if not segments:
        segments = [text_content[:2000]] if text_content else ["无内容"]

    api_endpoint = "https://api.fastdetect.net/api/detect"
    default_api_key = "sk-szcr9duUjGSmp6UaDQlsJku1zBG3Rr1NSjFoGLsvFb5VWVos"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key if api_key else default_api_key}",
    }

    results = []
    for segment in segments:
        payload = {
            "detector": "fast-detect(llama3-8b/llama3-8b-instruct)",
            "text": segment,
        }
        try:
            response = requests.post(api_endpoint, headers=headers, json=payload, timeout=30)
            response_data = response.json()
            probability = response_data.get("data", {}).get("prob", 0)
            details = response_data.get("data", {}).get("details", {})
        except Exception as exc:
            probability = 0
            details = str(exc)

        results.append({"text": segment, "prob": probability, "details": details})

    task.text_detection_results = results
    task.status = "completed"
    task.completion_time = timezone.now()
    task.save(update_fields=["status", "completion_time", "text_detection_results"])
    return "Paper detection finished"
