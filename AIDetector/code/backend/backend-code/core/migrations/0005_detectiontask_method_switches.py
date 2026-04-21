from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_alter_detectionresult_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="detectiontask",
            name="method_switches",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
