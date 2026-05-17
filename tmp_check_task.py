from django.utils import timezone
from core.models import DetectionTask, DetectionResult, SubDetectionResult

target = timezone.datetime(2026, 5, 11, 0, 51, 6)
tasks = DetectionTask.objects.filter(upload_time__year=2026, upload_time__month=5, upload_time__day=11)
print("Tasks today:")
for t in tasks:
    lt = timezone.localtime(t.upload_time)
    print("id=%d name=%s status=%s type=%s time=%s" % (t.id, t.task_name, t.status, t.task_type, lt))
    if t.status == 'in_progress':
        results = DetectionResult.objects.filter(detection_task=t)
        print("  Results: %d" % results.count())
        for r in results:
            print("    result id=%d status=%s image=%s" % (r.id, r.status, r.image_upload_id))
            subs = SubDetectionResult.objects.filter(detection_result=r)
            print("      SubResults: %d" % subs.count())
            for s in subs:
                print("        sub id=%d method=%s status=%s" % (s.id, s.method, s.status))
