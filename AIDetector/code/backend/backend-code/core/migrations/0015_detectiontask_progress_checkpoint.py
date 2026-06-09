# Generated manually — adds progress_percentage and checkpoint_data to DetectionTask
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0014_llmmodel_credit_total_llmmodel_credit_used_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="detectiontask",
            name="checkpoint_data",
            field=models.JSONField(blank=True, help_text="断点数据，用于失败后恢复检测", null=True),
        ),
        migrations.AddField(
            model_name="detectiontask",
            name="progress_percentage",
            field=models.IntegerField(default=0, help_text="检测进度百分比 0-100"),
        ),
    ]
