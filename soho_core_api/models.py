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



class Disks(models.Model):
    """
    مدل برای ذخیره اطلاعات یک دیسک سیستم.
    تمام اطلاعات از DiskManager.get_disk_info() ذخیره می‌شود.
    """
    disk_name = models.CharField(max_length=100, unique=True, db_index=True)
    model = models.CharField(max_length=255, blank=True)
    vendor = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=100, blank=True)
    device_path = models.TextField(blank=True)
    physical_block_size = models.CharField(max_length=10, blank=True)
    logical_block_size = models.CharField(max_length=10, blank=True)
    scheduler = models.CharField(max_length=255, blank=True)
    wwid = models.CharField(max_length=255, blank=True)
    total_bytes = models.BigIntegerField(null=True)
    temperature_celsius = models.IntegerField(null=True)
    wwn = models.CharField(max_length=255, blank=True)
    uuid = models.CharField(max_length=36, blank=True, null=True)
    slot_number = models.CharField(max_length=10, blank=True, null=True)
    disk_type = models.CharField(max_length=20, blank=True)
    has_partition = models.BooleanField(default=False)
    used_bytes = models.BigIntegerField(null=True)
    free_bytes = models.BigIntegerField(null=True)
    usage_percent = models.FloatField(null=True)
    partitions_data = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'disks'
        verbose_name = 'Disk'
        verbose_name_plural = 'Disks'

    def __str__(self):
        return f"Disks({self.disk_name})"
