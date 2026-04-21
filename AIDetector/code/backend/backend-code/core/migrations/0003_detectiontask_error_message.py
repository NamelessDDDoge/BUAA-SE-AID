from django.db import migrations, models


def add_error_message_column_if_missing(apps, schema_editor):
    table_name = "core_detectiontask"
    with schema_editor.connection.cursor() as cursor:
        columns = {
            row.name
            for row in schema_editor.connection.introspection.get_table_description(cursor, table_name)
        }
    if "error_message" in columns:
        return

    DetectionTask = apps.get_model("core", "DetectionTask")
    field = models.TextField(blank=True, null=True)
    field.set_attributes_from_name("error_message")
    schema_editor.add_field(DetectionTask, field)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_detectiontask_text_detection_results"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_error_message_column_if_missing,
                    reverse_code=migrations.RunPython.noop,
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="detectiontask",
                    name="error_message",
                    field=models.TextField(blank=True, null=True),
                )
            ],
        ),
    ]
