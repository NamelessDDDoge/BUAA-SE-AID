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


def _coerce_optional_int(value):
    if value is None or value == "":
        return None
    return int(value)


def _coerce_optional_float(value):
    if value is None or value == "":
        return None
    return float(value)


def backfill_review_results(apps, schema_editor):
    DetectionTask = apps.get_model("core", "DetectionTask")
    FileManagement = apps.get_model("core", "FileManagement")
    ReviewDetectionResult = apps.get_model("core", "ReviewDetectionResult")
    ReviewParagraphResult = apps.get_model("core", "ReviewParagraphResult")

    for task in DetectionTask.objects.filter(task_type="review").iterator():
        results = _sanitize_json_like(task.text_detection_results or {})
        if not isinstance(results, dict) or not results:
            continue

        document = results.get("document", {})
        paragraph_results = results.get("paragraph_results", [])
        suspicious_map = {
            item.get("paragraph_index"): item.get("explanation")
            for item in results.get("suspicious_paragraphs", [])
            if item.get("paragraph_index") is not None
        }
        relevance_map = {
            item.get("review_paragraph_index"): item
            for item in results.get("relevance_results", [])
            if item.get("review_paragraph_index") is not None
        }

        paper_file_id = document.get("paper_file_id")
        review_file_id = document.get("review_file_id")
        if paper_file_id and not FileManagement.objects.filter(id=paper_file_id).exists():
            paper_file_id = None
        if review_file_id and not FileManagement.objects.filter(id=review_file_id).exists():
            review_file_id = None

        review_result, _created = ReviewDetectionResult.objects.update_or_create(
            detection_task_id=task.id,
            defaults={
                "paper_file_id": paper_file_id,
                "review_file_id": review_file_id,
                "paper_segment_count": int(document.get("paper_segment_count") or 0),
                "review_segment_count": int(document.get("review_segment_count") or len(paragraph_results)),
            },
        )

        ReviewParagraphResult.objects.filter(review_detection_result_id=review_result.id).delete()
        ReviewParagraphResult.objects.bulk_create(
            [
                ReviewParagraphResult(
                    review_detection_result_id=review_result.id,
                    paragraph_index=int(item.get("paragraph_index", index)),
                    text=item.get("text", ""),
                    probability=float(item.get("probability") or 0.0),
                    label=item.get("label", ""),
                    details=item.get("details"),
                    suspicious_explanation=suspicious_map.get(item.get("paragraph_index", index)),
                    paper_paragraph_index=_coerce_optional_int(
                        relevance_map.get(item.get("paragraph_index", index), {}).get("paper_paragraph_index")
                    ),
                    paper_text=relevance_map.get(item.get("paragraph_index", index), {}).get("paper_text", ""),
                    relevance_score=_coerce_optional_float(
                        relevance_map.get(item.get("paragraph_index", index), {}).get("relevance_score")
                    ),
                    relevance_label=relevance_map.get(item.get("paragraph_index", index), {}).get("label", ""),
                    relevance_explanation=relevance_map.get(item.get("paragraph_index", index), {}).get("explanation"),
                )
                for index, item in enumerate(paragraph_results)
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_task_result_split"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReviewDetectionResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("paper_segment_count", models.IntegerField(default=0)),
                ("review_segment_count", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.localtime)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "detection_task",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="review_detection_result", to="core.detectiontask"),
                ),
                (
                    "paper_file",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="review_detection_results_as_paper", to="core.filemanagement"),
                ),
                (
                    "review_file",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="review_detection_results_as_review", to="core.filemanagement"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ReviewParagraphResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("paragraph_index", models.IntegerField()),
                ("text", models.TextField(blank=True, default="")),
                ("probability", models.FloatField(default=0.0)),
                ("label", models.CharField(blank=True, default="", max_length=32)),
                ("details", models.JSONField(blank=True, null=True)),
                ("suspicious_explanation", models.TextField(blank=True, null=True)),
                ("paper_paragraph_index", models.IntegerField(blank=True, null=True)),
                ("paper_text", models.TextField(blank=True, default="")),
                ("relevance_score", models.FloatField(blank=True, null=True)),
                ("relevance_label", models.CharField(blank=True, default="", max_length=32)),
                ("relevance_explanation", models.TextField(blank=True, null=True)),
                (
                    "review_detection_result",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="paragraph_results", to="core.reviewdetectionresult"),
                ),
            ],
            options={
                "ordering": ["paragraph_index"],
                "unique_together": {("review_detection_result", "paragraph_index")},
            },
        ),
        migrations.RunPython(backfill_review_results, migrations.RunPython.noop),
    ]
