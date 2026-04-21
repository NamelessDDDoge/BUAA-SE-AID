from pathlib import Path
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import DetectionResult, DetectionTask, SubDetectionResult


DEFAULT_CACHE_DIRS = (
    "temp",
    "ela_results",
    "llm_results",
    "masks",
    "reports",
)


class Command(BaseCommand):
    help = "Clear generated media artifacts used for local debugging and detection runs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be removed without changing files or database fields.",
        )
        parser.add_argument(
            "--include-uploads",
            action="store_true",
            help="Also remove uploads/ and extracted_images/. This is destructive and intended only for local debugging.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        include_uploads = options["include_uploads"]

        media_root = Path(settings.MEDIA_ROOT)
        target_dirs = list(DEFAULT_CACHE_DIRS)
        if include_uploads:
            target_dirs.extend(["uploads", "extracted_images"])

        removed_files = 0
        removed_dirs = 0

        for dirname in target_dirs:
            directory = media_root / dirname
            if not directory.exists():
                self.stdout.write(f"[skip] {directory} does not exist")
                continue

            for child in list(directory.iterdir()):
                if child.is_dir():
                    if dry_run:
                        self.stdout.write(f"[dry-run] remove dir {child}")
                    else:
                        shutil.rmtree(child, ignore_errors=True)
                    removed_dirs += 1
                else:
                    if dry_run:
                        self.stdout.write(f"[dry-run] remove file {child}")
                    else:
                        child.unlink(missing_ok=True)
                    removed_files += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run complete. Would remove {removed_files} files and {removed_dirs} directories."
                )
            )
            return

        with transaction.atomic():
            cleared_reports = DetectionTask.objects.exclude(report_file="").update(report_file=None)
            cleared_ela = DetectionResult.objects.exclude(ela_image="").update(ela_image=None)
            cleared_llm = DetectionResult.objects.exclude(llm_image="").update(llm_image=None)
            cleared_masks = SubDetectionResult.objects.exclude(mask_image="").update(mask_image=None)

            deleted_image_uploads = 0
            deleted_image_files = 0
            if include_uploads:
                from core.models import FileManagement, ImageUpload

                deleted_image_uploads = ImageUpload.objects.count()
                ImageUpload.objects.all().delete()
                image_file_qs = FileManagement.objects.filter(resource_type="image")
                deleted_image_files = image_file_qs.count()
                image_file_qs.delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Cleared media cache: "
                f"removed_files={removed_files}, removed_dirs={removed_dirs}, "
                f"report_refs={cleared_reports}, ela_refs={cleared_ela}, "
                f"llm_refs={cleared_llm}, mask_refs={cleared_masks}, "
                f"deleted_image_uploads={deleted_image_uploads}, deleted_image_files={deleted_image_files}"
            )
        )
