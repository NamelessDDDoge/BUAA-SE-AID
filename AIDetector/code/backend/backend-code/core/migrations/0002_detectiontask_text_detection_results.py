from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="detectiontask",
            name="text_detection_results",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
