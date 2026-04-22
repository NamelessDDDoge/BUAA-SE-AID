from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def _sanitize_json_like(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [_sanitize_json_like(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_json_like(item) for key, item in value.items()}
    return value


def backfill_paper_results(apps, schema_editor):
    DetectionTask = apps.get_model("core", "DetectionTask")
    FileManagement = apps.get_model("core", "FileManagement")
    PaperDetectionResult = apps.get_model("core", "PaperDetectionResult")
    PaperParagraphResult = apps.get_model("core", "PaperParagraphResult")
    PaperReferenceResult = apps.get_model("core", "PaperReferenceResult")

    for task in DetectionTask.objects.filter(task_type="paper").iterator():
        results = _sanitize_json_like(task.text_detection_results or {})
        if not isinstance(results, dict) or not results:
            continue

        document = results.get("document", {})
        paragraph_results = results.get("paragraph_results", [])
        explanation_map = {
            item.get("paragraph_index"): item.get("explanation")
            for item in results.get("suspicious_paragraphs", [])
            if item.get("paragraph_index") is not None
        }
        reference_results = results.get("reference_results", [])

        source_file_id = document.get("file_id")
        if source_file_id and not FileManagement.objects.filter(id=source_file_id).exists():
            source_file_id = None

        paper_result, _created = PaperDetectionResult.objects.update_or_create(
            detection_task_id=task.id,
            defaults={
                "source_file_id": source_file_id,
                "paragraph_count": int(document.get("paragraph_count") or len(paragraph_results)),
                "segment_count": int(document.get("segment_count") or len(paragraph_results)),
                "reference_count": int(document.get("reference_count") or len(reference_results)),
                "image_detection_enabled": bool(document.get("image_detection_enabled", True)),
            },
        )

        PaperParagraphResult.objects.filter(paper_detection_result_id=paper_result.id).delete()
        PaperParagraphResult.objects.bulk_create(
            [
                PaperParagraphResult(
                    paper_detection_result_id=paper_result.id,
                    paragraph_index=int(item.get("paragraph_index", index)),
                    text=item.get("text", ""),
                    probability=float(item.get("probability") or 0.0),
                    label=item.get("label", ""),
                    details=item.get("details"),
                    explanation=explanation_map.get(item.get("paragraph_index", index)),
                )
                for index, item in enumerate(paragraph_results)
            ]
        )

        PaperReferenceResult.objects.filter(paper_detection_result_id=paper_result.id).delete()
        PaperReferenceResult.objects.bulk_create(
            [
                PaperReferenceResult(
                    paper_detection_result_id=paper_result.id,
                    reference_index=int(item.get("reference_index", index)),
                    reference=item.get("reference", ""),
                    exists=bool(item.get("exists", False)),
                    is_relevant=bool(item.get("is_relevant", False)),
                    overlap_terms=item.get("overlap_terms") or [],
                )
                for index, item in enumerate(reference_results)
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_detectiontask_method_switches"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaperDetectionResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("paragraph_count", models.IntegerField(default=0)),
                ("segment_count", models.IntegerField(default=0)),
                ("reference_count", models.IntegerField(default=0)),
                ("image_detection_enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.localtime)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "detection_task",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="paper_detection_result", to="core.detectiontask"),
                ),
                (
                    "source_file",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="paper_detection_results", to="core.filemanagement"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PaperParagraphResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("paragraph_index", models.IntegerField()),
                ("text", models.TextField(blank=True, default="")),
                ("probability", models.FloatField(default=0.0)),
                ("label", models.CharField(blank=True, default="", max_length=32)),
                ("details", models.JSONField(blank=True, null=True)),
                ("explanation", models.TextField(blank=True, null=True)),
                (
                    "paper_detection_result",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="paragraph_results", to="core.paperdetectionresult"),
                ),
            ],
            options={
                "ordering": ["paragraph_index"],
                "unique_together": {("paper_detection_result", "paragraph_index")},
            },
        ),
        migrations.CreateModel(
            name="PaperReferenceResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference_index", models.IntegerField()),
                ("reference", models.TextField(blank=True, default="")),
                ("exists", models.BooleanField(default=False)),
                ("is_relevant", models.BooleanField(default=False)),
                ("overlap_terms", models.JSONField(blank=True, default=list)),
                (
                    "paper_detection_result",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reference_results", to="core.paperdetectionresult"),
                ),
            ],
            options={
                "ordering": ["reference_index"],
                "unique_together": {("paper_detection_result", "reference_index")},
            },
        ),
        migrations.RunPython(backfill_paper_results, migrations.RunPython.noop),
    ]
