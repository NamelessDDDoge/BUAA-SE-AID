from django.contrib import admin

# Register your models here.

from .models import User, FileManagement, ImageUpload, DetectionResult, ReviewRequest, ManualReview, Feedback, Log, DetectionTask
admin.site.register(User)
admin.site.register(FileManagement)
admin.site.register(ImageUpload)
admin.site.register(DetectionResult)
admin.site.register(ReviewRequest)
admin.site.register(ManualReview)
admin.site.register(Feedback)
admin.site.register(Log)
admin.site.register(DetectionTask)