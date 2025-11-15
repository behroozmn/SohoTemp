from django.db import models
from django.utils import timezone



class StandardResponseModel(models.Model):
    ok = models.BooleanField(default=True)
    message = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    details = models.JSONField(default=dict, blank=True)
    meta = models.JSONField()
    request_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Success Response @ {self.created_at.isoformat()}"

    class Meta:
        db_table = 'StandardResponse'


class StandardErrorResponseModel(models.Model):
    ok = models.BooleanField(default=False)
    error_code = models.CharField(max_length=100)
    error_message = models.TextField()
    error_extra = models.JSONField(default=dict, blank=True)
    meta = models.JSONField()
    request_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Error Response [{self.error_code}] @ {self.created_at.isoformat()}"

    class Meta:
        db_table = 'StandardResponseError'