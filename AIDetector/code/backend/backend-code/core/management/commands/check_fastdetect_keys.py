"""Management command: 探测所有 active FastDetect key 的健康状态并写入 DB。

用法:
    python manage.py check_fastdetect_keys
    python manage.py check_fastdetect_keys --model-id 3
    python manage.py check_fastdetect_keys --timeout 30
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from core.models import LLMModel
from core.services.capabilities.llm.health import (
    AVAILABLE,
    ERROR,
    EXHAUSTED,
    INVALID,
    check_single_model,
)

STATUS_ICON = {
    AVAILABLE: "✓",
    EXHAUSTED: "⚠",
    INVALID: "✗",
    ERROR: "✗",
}


class Command(BaseCommand):
    help = "Probe all active FastDetect keys and persist health status to DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--model-id",
            type=int,
            default=None,
            help="Only check the model with this primary key.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=15,
            help="Request timeout in seconds (default 15).",
        )

    def handle(self, *args, **options):
        qs = LLMModel.objects.filter(model_type="fastdetect", is_active=True)
        if options["model_id"]:
            qs = qs.filter(pk=options["model_id"])

        if not qs.exists():
            self.stdout.write(self.style.WARNING("No active FastDetect models found."))
            return

        timeout = options["timeout"]
        results = []
        for model in qs.iterator():
            self.stdout.write(f"  Checking #{model.pk} {model.display_name} ... ", ending="")
            self.stdout.flush()
            try:
                status, detail = check_single_model(model, timeout=timeout)
            except Exception as exc:
                status, detail = ERROR, str(exc)
                # 兜底：确保 DB 有记录
                from core.services.capabilities.llm.health import update_model_health
                update_model_health(model, ERROR, detail)
            icon = STATUS_ICON.get(status, "?")
            self.stdout.write(f"{icon} {status}  {detail[:120]}")
            results.append((model.pk, model.display_name, status, detail))

        # 汇总
        counts = {s: 0 for s in (AVAILABLE, EXHAUSTED, INVALID, ERROR)}
        for _, _, s, _ in results:
            counts[s] = counts.get(s, 0) + 1
        parts = [f"{k}: {v}" for k, v in counts.items() if v > 0]
        self.stdout.write(self.style.SUCCESS(f"Done. {' | '.join(parts)}  total={len(results)}"))
