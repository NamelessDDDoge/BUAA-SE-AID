"""Backend performance smoke test for task submission paths.

This script measures API response and task-creation latency only. It mocks
asynchronous detection starters, so it does not call GPU inference or external
LLM/FastDetect services.

Example:
    env HOME=/tmp/buaa-se-aid-home conda run -n se python tests/performance/run_aid_perf.py
"""

import json
import logging
import os
import platform
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "AIDetector" / "code" / "backend" / "backend-code"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_settings")
os.environ.setdefault("DATABASE_MODE", "local")
os.environ.setdefault("LOCAL_DB_NAME", "/tmp/buaa-se-aid-perf.sqlite3")
sys.path.insert(0, str(BACKEND_DIR))

import django
from django.conf import settings
from django.core.management import call_command
from django.db import close_old_connections


django.setup()
settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver"]
settings.DATABASES["default"].setdefault("OPTIONS", {})["timeout"] = 30
logging.getLogger("django.request").setLevel(logging.CRITICAL)

from rest_framework.test import APIClient

from core.models import DetectionTask, FileManagement, ImageUpload, Organization, User


def percentile(values, percent):
    values = sorted(values)
    if not values:
        return 0.0
    index = int(round((len(values) - 1) * percent / 100))
    return values[index]


def summarize(latencies):
    return {
        "count": len(latencies),
        "avg_ms": round(statistics.mean(latencies), 2),
        "min_ms": round(min(latencies), 2),
        "p50_ms": round(percentile(latencies, 50), 2),
        "p95_ms": round(percentile(latencies, 95), 2),
        "max_ms": round(max(latencies), 2),
    }


def timed_call(fn):
    start = time.perf_counter()
    response = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return response, elapsed_ms


def make_client(user):
    client = APIClient()
    client.raise_request_exception = False
    client.force_authenticate(user=user)
    return client


def post_json(client, path, data):
    return client.post(path, data=data, format="json")


def get(client, path):
    return client.get(path)


def create_org_and_users():
    org = Organization.objects.create(
        name="Perf Org 20260525",
        email="perf-org-20260525@example.com",
        remaining_non_llm_uses=100000,
        remaining_llm_uses=100000,
    )
    users = [
        User.objects.create_user(
            username=f"perf_user_{i}",
            email=f"perf_user_{i}@example.com",
            password="pass123456",
            role="publisher",
            organization=org,
        )
        for i in range(25)
    ]
    return org, users


def create_image_uploads(users, total):
    uploads = []
    for i in range(total):
        user = users[i % len(users)]
        file_record = FileManagement.objects.create(
            user=user,
            organization=user.organization,
            file_name=f"perf_image_{i}.png",
            file_size=4096,
            file_type="image/png",
            resource_type="image",
            stored_path=f"uploads/perf_image_{i}.png",
            tag="Other",
        )
        uploads.append(
            ImageUpload.objects.create(
                file_management=file_record,
                image=f"extracted_images/perf_image_{i}.png",
            )
        )
    return uploads


def create_resource_files(users, total):
    papers = []
    review_pairs = []
    for i in range(total):
        user = users[i % len(users)]
        papers.append(
            FileManagement.objects.create(
                user=user,
                organization=user.organization,
                file_name=f"perf_paper_{i}.pdf",
                file_size=8192,
                file_type="application/pdf",
                resource_type="paper",
                stored_path=f"uploads/perf_paper_{i}.pdf",
            )
        )

        review_paper = FileManagement.objects.create(
            user=user,
            organization=user.organization,
            file_name=f"perf_review_paper_{i}.pdf",
            file_size=8192,
            file_type="application/pdf",
            resource_type="review_paper",
            stored_path=f"uploads/perf_review_paper_{i}.pdf",
        )
        review_file = FileManagement.objects.create(
            user=user,
            organization=user.organization,
            file_name=f"perf_review_{i}.txt",
            file_size=2048,
            file_type="text/plain",
            resource_type="review_file",
            stored_path=f"uploads/perf_review_{i}.txt",
            linked_file=review_paper,
        )
        review_pairs.append((review_paper, review_file))
    return papers, review_pairs


def run_sequential(label, calls):
    latencies = []
    statuses = []
    total_start = time.perf_counter()
    for call in calls:
        response, elapsed = timed_call(call)
        latencies.append(elapsed)
        statuses.append(response.status_code)
    total = time.perf_counter() - total_start
    ok = sum(1 for code in statuses if 200 <= code < 300)
    return {
        "label": label,
        "success": ok,
        "failed": len(statuses) - ok,
        "throughput_rps": round(len(statuses) / total, 2),
        **summarize(latencies),
    }


def run_concurrent(label, jobs, workers):
    latencies = []
    statuses = []
    total_start = time.perf_counter()

    def worker(job):
        close_old_connections()
        try:
            response, elapsed = timed_call(job)
            return response.status_code, elapsed
        except Exception:
            return 500, 0.0
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(worker, job) for job in jobs]
        for future in as_completed(futures):
            status, elapsed = future.result()
            statuses.append(status)
            latencies.append(elapsed)

    total = time.perf_counter() - total_start
    ok = sum(1 for code in statuses if isinstance(code, int) and 200 <= code < 300)
    return {
        "label": label,
        "workers": workers,
        "success": ok,
        "failed": len(statuses) - ok,
        "throughput_rps": round(len(statuses) / total, 2),
        **summarize(latencies),
    }


def main():
    call_command("migrate", interactive=False, verbosity=0)
    Organization.objects.filter(name="Perf Org 20260525").delete()

    _org, users = create_org_and_users()
    images = create_image_uploads(users, 220)
    papers, review_pairs = create_resource_files(users, 140)

    def noop_start(*_args, **_kwargs):
        return None

    results = []
    with patch("core.views.views_dectection._start_detection_task_thread", side_effect=noop_start), patch(
        "core.views.views_dectection.start_resource_detection_task_thread", side_effect=noop_start
    ):
        user_client = make_client(users[0])
        results.append(
            run_sequential(
                "轻量用户详情接口响应",
                [lambda client=user_client: get(client, "/api/user/details/") for _ in range(100)],
            )
        )

        seq_image_calls = []
        for image in images[:50]:
            client = make_client(image.file_management.user)
            seq_image_calls.append(
                lambda client=client, image_id=image.id: post_json(
                    client,
                    "/api/detection/submit/",
                    {
                        "image_ids": [image_id],
                        "task_name": "性能测试图片任务",
                        "mode": 1,
                        "method_switches": {"ela": True, "exif": True, "cmd": True, "urn": True},
                        "if_use_llm": False,
                    },
                )
            )
        results.append(run_sequential("图片检测任务提交响应", seq_image_calls))

        seq_resource_calls = []
        for paper in papers[:50]:
            client = make_client(paper.user)
            seq_resource_calls.append(
                lambda client=client, file_id=paper.id: post_json(
                    client,
                    "/api/resource-task/create/",
                    {
                        "task_type": "paper",
                        "file_ids": [file_id],
                        "task_name": "性能测试论文任务",
                        "method_switches": {"llm": False},
                    },
                )
            )
        results.append(run_sequential("论文检测任务提交响应", seq_resource_calls))

        concurrent_image_jobs = []
        for image in images[50:150]:
            client = make_client(image.file_management.user)
            concurrent_image_jobs.append(
                lambda client=client, image_id=image.id: post_json(
                    client,
                    "/api/detection/submit/",
                    {
                        "image_ids": [image_id],
                        "task_name": "并发图片任务",
                        "mode": 1,
                        "method_switches": {"ela": True, "exif": True, "cmd": True, "urn": True},
                        "if_use_llm": False,
                    },
                )
            )
        results.append(run_concurrent("多用户并发图片任务提交", concurrent_image_jobs, workers=20))

        mixed_resource_jobs = []
        paper_cycle = cycle(papers[50:90])
        review_cycle = cycle(review_pairs[50:90])
        user_cycle = cycle(users)
        for i in range(80):
            user = next(user_cycle)
            client = make_client(user)
            if i % 2 == 0:
                paper = next(paper_cycle)
                client = make_client(paper.user)
                mixed_resource_jobs.append(
                    lambda client=client, file_id=paper.id: post_json(
                        client,
                        "/api/resource-task/create/",
                        {
                            "task_type": "paper",
                            "file_ids": [file_id],
                            "task_name": "并发论文任务",
                            "method_switches": {"llm": False},
                        },
                    )
                )
            else:
                review_paper, review_file = next(review_cycle)
                client = make_client(review_paper.user)
                mixed_resource_jobs.append(
                    lambda client=client, paper_id=review_paper.id, review_id=review_file.id: post_json(
                        client,
                        "/api/resource-task/create/",
                        {
                            "task_type": "review",
                            "file_ids": [paper_id, review_id],
                            "task_name": "并发Review任务",
                            "method_switches": {"llm": False},
                        },
                    )
                )
        results.append(run_concurrent("多用户并发论文/Review任务提交", mixed_resource_jobs, workers=4))

    task_names = ["性能测试图片任务", "性能测试论文任务", "并发图片任务", "并发论文任务", "并发Review任务"]
    status_counts = Counter(
        DetectionTask.objects.filter(task_name__in=task_names).values_list("status", flat=True)
    )
    output = {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "database": os.environ.get("LOCAL_DB_NAME"),
            "mode": os.environ.get("DATABASE_MODE"),
            "gpu_or_external_api": "not invoked; async starters mocked",
        },
        "results": results,
        "created_tasks": DetectionTask.objects.filter(task_name__in=task_names).count(),
        "task_statuses": dict(status_counts),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    Path(os.environ.get("HOME", "/tmp")).mkdir(parents=True, exist_ok=True)
    main()
