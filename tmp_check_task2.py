from django.utils import timezone
from core.models import DetectionTask, DetectionResult, SubDetectionResult, ImageUpload

t = DetectionTask.objects.get(id=181)
print("Task id=%d status=%s type=%s" % (t.id, t.status, t.task_type))
print("Upload time:", timezone.localtime(t.upload_time))

img = ImageUpload.objects.get(id=488)
print("Image id=%d stored=%s" % (img.id, img.stored_path))

results = DetectionResult.objects.filter(detection_task=t)
for r in results:
    print("Result id=%d status=%s image=%s" % (r.id, r.status, r.image_upload_id))
    subs = SubDetectionResult.objects.filter(detection_result=r)
    for s in subs:
        print("  Sub id=%d method=%s status=%s" % (s.id, s.method, s.status))
    if subs.count() == 0:
        print("  No SubDetectionResults - detection never ran")
