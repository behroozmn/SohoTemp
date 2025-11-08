from django.db import models
from django.utils import timezone





class StandardErrorResponseLog(models.Model):
    ok = models.BooleanField(default=False)
    error_code = models.CharField(max_length=100)
    error_message = models.TextField()
    error_extra = models.JSONField(default=dict, blank=True)
    meta = models.JSONField()
    request_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Error Response [{self.error_code}] @ {self.created_at.isoformat()}"