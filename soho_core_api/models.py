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

    # 🔹 فیلد جدید: زمان آخرین بروزرسانی
    last_update = models.DateTimeField(auto_now=True, db_index=True) # TODO: زمان باید براساس تایم‌زون باشه

    class Meta:
        db_table = 'disks'
        verbose_name = 'Disk'
        verbose_name_plural = 'Disks'

    def __str__(self):
        return f"Disks({self.disk_name})"

class Pools(models.Model):
    # فیلدهای اصلی pool (همان‌هایی که در خروجی get_pool_detail هستند)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    health = models.CharField(max_length=50, blank=True)
    size = models.CharField(max_length=50, blank=True)
    allocated = models.CharField(max_length=50, blank=True)
    free = models.CharField(max_length=50, blank=True)
    capacity = models.CharField(max_length=50, blank=True)  # مثلاً "20%"
    guid = models.CharField(max_length=100, blank=True)
    vdev_type = models.CharField(max_length=50, blank=True)  # mirror, raidz1, disk, ...

    # دیگر فیلدهای متداول (اختیاری ولی پیشنهادی برای پوشش کامل)
    autoreplace = models.CharField(max_length=10, blank=True)  # "on"/"off"
    autoexpand = models.CharField(max_length=10, blank=True)
    autotrim = models.CharField(max_length=10, blank=True)
    dedupratio = models.CharField(max_length=20, blank=True)
    fragmentation = models.CharField(max_length=20, blank=True)
    readonly = models.CharField(max_length=10, blank=True)
    failmode = models.CharField(max_length=20, blank=True)
    version = models.CharField(max_length=20, blank=True)

    # 🔸 فیلد disks به صورت JSON ساختاریافته
    disks = models.JSONField(default=list, blank=True)

    # زمان آخرین بروزرسانی
    last_update = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = 'pools'
        verbose_name = 'pool'
        verbose_name_plural = 'pools'

    def __str__(self):
        return f"Pools({self.name})"

class Filesystems(models.Model):
    name = models.CharField(max_length=255, unique=True, db_index=True)
    pool_name = models.CharField(max_length=255, db_index=True)

    # تمام فیلدهای خروجی API — دقیقاً همان نام و به صورت رشته‌ای
    available = models.CharField(max_length=50, blank=True)
    compressratio = models.CharField(max_length=20, blank=True)
    createtxg = models.CharField(max_length=30, blank=True)
    creation = models.CharField(max_length=50, blank=True)
    encryptionroot = models.CharField(max_length=255, blank=True)
    filesystem_count = models.CharField(max_length=20, blank=True)
    guid = models.CharField(max_length=50, blank=True)
    inconsistent = models.CharField(max_length=10, blank=True)
    ivsetguid = models.CharField(max_length=255, blank=True)
    keyguid = models.CharField(max_length=255, blank=True)
    keystatus = models.CharField(max_length=50, blank=True)
    logicalreferenced = models.CharField(max_length=50, blank=True)
    logicalused = models.CharField(max_length=50, blank=True)
    mounted = models.CharField(max_length=10, blank=True)
    objsetid = models.CharField(max_length=30, blank=True)
    origin = models.CharField(max_length=255, blank=True)
    prevsnap = models.CharField(max_length=255, blank=True)
    receive_resume_token = models.CharField(max_length=255, blank=True)
    redact_snaps = models.CharField(max_length=255, blank=True)
    redacted = models.CharField(max_length=10, blank=True)
    refcompressratio = models.CharField(max_length=20, blank=True)
    referenced = models.CharField(max_length=50, blank=True)
    remaptxg = models.CharField(max_length=30, blank=True)
    snapshot_count = models.CharField(max_length=20, blank=True)
    type = models.CharField(max_length=20, blank=True)
    unique = models.CharField(max_length=50, blank=True)
    used = models.CharField(max_length=50, blank=True)
    usedbychildren = models.CharField(max_length=50, blank=True)
    usedbydataset = models.CharField(max_length=50, blank=True)
    usedbyrefreservation = models.CharField(max_length=50, blank=True)
    usedbysnapshots = models.CharField(max_length=50, blank=True)
    useraccounting = models.CharField(max_length=10, blank=True)
    written = models.CharField(max_length=50, blank=True)

    # Propertyهای ZFS
    aclinherit = models.CharField(max_length=50, blank=True)
    aclmode = models.CharField(max_length=50, blank=True)
    acltype = models.CharField(max_length=50, blank=True)
    atime = models.CharField(max_length=10, blank=True)
    canmount = models.CharField(max_length=50, blank=True)
    casesensitivity = models.CharField(max_length=50, blank=True)
    checksum = models.CharField(max_length=10, blank=True)
    compression = models.CharField(max_length=10, blank=True)
    context = models.CharField(max_length=50, blank=True)
    copies = models.CharField(max_length=10, blank=True)
    dedup = models.CharField(max_length=10, blank=True)
    defcontext = models.CharField(max_length=50, blank=True)
    devices = models.CharField(max_length=10, blank=True)
    dnodesize = models.CharField(max_length=20, blank=True)
    encryption = models.CharField(max_length=10, blank=True)
    exec = models.CharField(max_length=10, blank=True)
    filesystem_limit = models.CharField(max_length=20, blank=True)
    fscontext = models.CharField(max_length=50, blank=True)
    keyformat = models.CharField(max_length=50, blank=True)
    keylocation = models.CharField(max_length=255, blank=True)
    logbias = models.CharField(max_length=20, blank=True)
    mlslabel = models.CharField(max_length=50, blank=True)
    mountpoint = models.CharField(max_length=255, blank=True)
    nbmand = models.CharField(max_length=10, blank=True)
    normalization = models.CharField(max_length=50, blank=True)
    overlay = models.CharField(max_length=10, blank=True)
    pbkdf2iters = models.CharField(max_length=20, blank=True)
    pbkdf2salt = models.CharField(max_length=20, blank=True)
    primarycache = models.CharField(max_length=20, blank=True)
    quota = models.CharField(max_length=50, blank=True)
    readonly = models.CharField(max_length=10, blank=True)
    recordsize = models.CharField(max_length=20, blank=True)
    redundant_metadata = models.CharField(max_length=20, blank=True)
    refquota = models.CharField(max_length=50, blank=True)
    refreservation = models.CharField(max_length=50, blank=True)
    relatime = models.CharField(max_length=10, blank=True)
    reservation = models.CharField(max_length=50, blank=True)
    rootcontext = models.CharField(max_length=50, blank=True)
    secondarycache = models.CharField(max_length=20, blank=True)
    setuid = models.CharField(max_length=10, blank=True)
    sharenfs = models.CharField(max_length=10, blank=True)
    sharesmb = models.CharField(max_length=10, blank=True)
    snapdev = models.CharField(max_length=20, blank=True)
    snapdir = models.CharField(max_length=20, blank=True)
    snapshot_limit = models.CharField(max_length=20, blank=True)
    special_small_blocks = models.CharField(max_length=20, blank=True)
    sync = models.CharField(max_length=20, blank=True)
    utf8only = models.CharField(max_length=10, blank=True)
    version = models.CharField(max_length=20, blank=True)
    volmode = models.CharField(max_length=20, blank=True)
    vscan = models.CharField(max_length=10, blank=True)
    xattr = models.CharField(max_length=10, blank=True)
    zoned = models.CharField(max_length=10, blank=True)

    last_update = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = 'filesystems'
        verbose_name = 'Filesystem'
        verbose_name_plural = 'Filesystems'

    def __str__(self):
        return f"Filesystems({self.name})"