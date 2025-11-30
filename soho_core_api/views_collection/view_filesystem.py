# soho_core_api/views/view_filesystem.py

from __future__ import annotations

from typing import Any, Dict, Optional, List, Union
from rest_framework.views import APIView


from pylibs import get_request_param, build_standard_error_response
from pylibs.fileSystem import FilesystemManager
from pylibs.mixins import ZpoolValidationMixin, FilesystemValidationMixin
from pylibs import StandardResponse, StandardErrorResponse
from soho_core_api.models import Filesystems

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.request import Request
from rest_framework.response import Response


def db_update_filesystem_single(fs_data: Dict[str, Any]) -> None:
    if not isinstance(fs_data, dict) or 'name' not in fs_data:
        return
    full_name = fs_data['name']
    pool_name = full_name.split('/')[0] if '/' in full_name else full_name

    defaults = {
        'pool_name': pool_name,
        'available': fs_data.get('available', ''),
        'compressratio': fs_data.get('compressratio', ''),
        'createtxg': fs_data.get('createtxg', ''),
        'creation': fs_data.get('creation', ''),
        'encryptionroot': fs_data.get('encryptionroot', ''),
        'filesystem_count': fs_data.get('filesystem_count', ''),
        'guid': fs_data.get('guid', ''),
        'inconsistent': fs_data.get('inconsistent', ''),
        'ivsetguid': fs_data.get('ivsetguid', ''),
        'keyguid': fs_data.get('keyguid', ''),
        'keystatus': fs_data.get('keystatus', ''),
        'logicalreferenced': fs_data.get('logicalreferenced', ''),
        'logicalused': fs_data.get('logicalused', ''),
        'mounted': fs_data.get('mounted', ''),
        'objsetid': fs_data.get('objsetid', ''),
        'origin': fs_data.get('origin', ''),
        'prevsnap': fs_data.get('prevsnap', ''),
        'receive_resume_token': fs_data.get('receive_resume_token', ''),
        'redact_snaps': fs_data.get('redact_snaps', ''),
        'redacted': fs_data.get('redacted', ''),
        'refcompressratio': fs_data.get('refcompressratio', ''),
        'referenced': fs_data.get('referenced', ''),
        'remaptxg': fs_data.get('remaptxg', ''),
        'snapshot_count': fs_data.get('snapshot_count', ''),
        'type': fs_data.get('type', ''),
        'unique': fs_data.get('unique', ''),
        'used': fs_data.get('used', ''),
        'usedbychildren': fs_data.get('usedbychildren', ''),
        'usedbydataset': fs_data.get('usedbydataset', ''),
        'usedbyrefreservation': fs_data.get('usedbyrefreservation', ''),
        'usedbysnapshots': fs_data.get('usedbysnapshots', ''),
        'useraccounting': fs_data.get('useraccounting', ''),
        'written': fs_data.get('written', ''),

        # ZFS properties
        'aclinherit': fs_data.get('aclinherit', ''),
        'aclmode': fs_data.get('aclmode', ''),
        'acltype': fs_data.get('acltype', ''),
        'atime': fs_data.get('atime', ''),
        'canmount': fs_data.get('canmount', ''),
        'casesensitivity': fs_data.get('casesensitivity', ''),
        'checksum': fs_data.get('checksum', ''),
        'compression': fs_data.get('compression', ''),
        'context': fs_data.get('context', ''),
        'copies': fs_data.get('copies', ''),
        'dedup': fs_data.get('dedup', ''),
        'defcontext': fs_data.get('defcontext', ''),
        'devices': fs_data.get('devices', ''),
        'dnodesize': fs_data.get('dnodesize', ''),
        'encryption': fs_data.get('encryption', ''),
        'exec': fs_data.get('exec', ''),
        'filesystem_limit': fs_data.get('filesystem_limit', ''),
        'fscontext': fs_data.get('fscontext', ''),
        'keyformat': fs_data.get('keyformat', ''),
        'keylocation': fs_data.get('keylocation', ''),
        'logbias': fs_data.get('logbias', ''),
        'mlslabel': fs_data.get('mlslabel', ''),
        'mountpoint': fs_data.get('mountpoint', ''),
        'nbmand': fs_data.get('nbmand', ''),
        'normalization': fs_data.get('normalization', ''),
        'overlay': fs_data.get('overlay', ''),
        'pbkdf2iters': fs_data.get('pbkdf2iters', ''),
        'pbkdf2salt': fs_data.get('pbkdf2salt', ''),
        'primarycache': fs_data.get('primarycache', ''),
        'quota': fs_data.get('quota', ''),
        'readonly': fs_data.get('readonly', ''),
        'recordsize': fs_data.get('recordsize', ''),
        'redundant_metadata': fs_data.get('redundant_metadata', ''),
        'refquota': fs_data.get('refquota', ''),
        'refreservation': fs_data.get('refreservation', ''),
        'relatime': fs_data.get('relatime', ''),
        'reservation': fs_data.get('reservation', ''),
        'rootcontext': fs_data.get('rootcontext', ''),
        'secondarycache': fs_data.get('secondarycache', ''),
        'setuid': fs_data.get('setuid', ''),
        'sharenfs': fs_data.get('sharenfs', ''),
        'sharesmb': fs_data.get('sharesmb', ''),
        'snapdev': fs_data.get('snapdev', ''),
        'snapdir': fs_data.get('snapdir', ''),
        'snapshot_limit': fs_data.get('snapshot_limit', ''),
        'special_small_blocks': fs_data.get('special_small_blocks', ''),
        'sync': fs_data.get('sync', ''),
        'utf8only': fs_data.get('utf8only', ''),
        'version': fs_data.get('version', ''),
        'volmode': fs_data.get('volmode', ''),
        'vscan': fs_data.get('vscan', ''),
        'xattr': fs_data.get('xattr', ''),
        'zoned': fs_data.get('zoned', ''),
    }

    Filesystems.objects.update_or_create(name=full_name, defaults=defaults)


def db_sync_filesystems(filesystems_list: List[Dict[str, Any]]) -> None:
    if not isinstance(filesystems_list, list):
        raise ValueError("ورودی باید لیستی از دیکشنری‌ها باشد.")

    current_names = {fs['name'] for fs in filesystems_list if isinstance(fs, dict) and 'name' in fs}
    Filesystems.objects.exclude(name__in=current_names).delete()

    for fs in filesystems_list:
        if isinstance(fs, dict) and 'name' in fs:
            db_update_filesystem_single(fs)


class FilesystemListView(APIView, ZpoolValidationMixin, FilesystemValidationMixin):
    """View برای عملیات دسته‌جمعی روی فایل‌سیستم‌ها."""

    @extend_schema(parameters=[OpenApiParameter(name="detail", type=bool, required=False, description="دریافت جزئیات کامل فایل‌سیستم‌ها در صورت True", ),
                               OpenApiParameter(name="contain_poolname", type=bool, required=False, description="در صورت True، نام پول مربوطه در خروجی گنجانده می‌شود"),
                               OpenApiParameter(name="save_to_db", type=bool, required=False, description="در صورت True، داده‌ها در دیتابیس ذخیره می‌شوند")])
    def get(self, request: Request) -> Response:
        """دریافت لیست نام تمام فایل‌سیستم‌ها یا جزئیات کامل آن‌ها."""

        save_to_db = get_request_param(request, "save_to_db", bool, False)
        detail = get_request_param(request, "detail", bool, False)
        contain_poolname = get_request_param(request, "contain_poolname", bool, False)
        request_data = dict(request.query_params)
        try:
            fs_manager = FilesystemManager()
            if detail:
                data = fs_manager.get_filesystems_all_detail(contain_poolname=contain_poolname)
                if save_to_db:
                    db_sync_filesystems(data)
            else:
                data = fs_manager.list_filesystems_names(contain_poolname=contain_poolname)

            return StandardResponse(data=data, request_data=request_data, save_to_db=save_to_db,
                                    message="لیست فایل‌سیستم‌ها با موفقیت بازیابی شد.", )
        except Exception as exc:
            return build_standard_error_response(exc=exc, request_data=request_data, save_to_db=save_to_db,
                                                 error_code="filesystem_list_failed",
                                                 error_message="خطا در دریافت لیست فایل‌سیستم‌ها.")


class FilesystemDetailView(APIView, ZpoolValidationMixin, FilesystemValidationMixin):
    """View برای عملیات روی یک فایل‌سیستم خاص."""

    @extend_schema(parameters=[OpenApiParameter(name="property", type=str, required=False, description="نام پراپرتی برای بازیابی (مثلاً mountpoint). اگر all یا خالی باشد، تمام جزئیات برگردانده می‌شود."),
                               OpenApiParameter(name="save_to_db", type=bool, required=False, description="در صورت True، داده‌ها در دیتابیس ذخیره می‌شوند")])
    def get(self, request: Request, pool_name: str, fs_name: str) -> Response:
        """
            دریافت جزئیات یک فایل‌سیستم

            QueryParameter:

                ---> property=value [all , mountpoint, name , ... ]

                ---> save_to_db=True|False
        """
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        prop_key = get_request_param(request, "property", str, None)
        request_data = dict(request.query_params)

        try:
            pool_manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
            if isinstance(pool_manager, StandardErrorResponse):
                return pool_manager

            full_name = f"{pool_name}/{fs_name}"
            fs_manager = FilesystemManager()

            if prop_key and prop_key.lower() != "all":
                value = fs_manager.get_filesystem_property(full_name, prop_key)
                if value is None:
                    return StandardErrorResponse(request_data=request_data, save_to_db=save_to_db, status=404,
                                                 error_code="property_not_found",
                                                 error_message=f"پراپرتی '{prop_key}' در فایل‌سیستم '{full_name}' یافت نشد.")
                return StandardResponse(request_data=request_data, save_to_db=save_to_db,
                                        data={prop_key: value},
                                        message=f"پراپرتی '{prop_key}' با موفقیت بازیابی شد.")
            else:
                detail = fs_manager.get_filesystem_detail(full_name)
                if detail is None:
                    return StandardErrorResponse(request_data=request_data, save_to_db=save_to_db, status=404,
                                                 error_code="filesystem_not_found",
                                                 error_message=f"فایل‌سیستم '{full_name}' یافت نشد.")
                if save_to_db:
                    db_update_filesystem_single(detail)
                return StandardResponse(data=detail, request_data=request_data, save_to_db=save_to_db,
                                        message="جزئیات فایل‌سیستم با موفقیت بازیابی شد.")

        except Exception as exc:
            return build_standard_error_response(exc=exc, request_data=request_data, save_to_db=save_to_db,
                                                 error_code="filesystem_detail_failed",
                                                 error_message="خطا در دریافت جزئیات فایل‌سیستم.")

    @extend_schema(parameters=[OpenApiParameter(name="save_to_db", type=bool, required=False, description="ذخیره در دیتابیس"),
                               OpenApiParameter(name="quota", type=str, required=False, description="سهمیه فایل‌سیستم (مثلاً 10G)"),
                               OpenApiParameter(name="reservation", type=str, required=False, description="رزرو فضای فایل‌سیستم"),
                               OpenApiParameter(name="mountpoint", type=str, required=False, description="نقطه اتصال فایل‌سیستم که میتواند خالی باشد")])
    def post(self, request: Request, pool_name: str, fs_name: str) -> Response:
        """ساخت فایل‌سیستم جدید."""
        save_to_db: bool = get_request_param(request, "save_to_db", bool, False)
        quota = get_request_param(request, "quota", str, None)
        reservation = get_request_param(request, "reservation", str, None)
        mountpoint: str = get_request_param(request, "mountpoint", str, None)
        request_data = dict(request.data)

        pool_manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(pool_manager, StandardErrorResponse):
            return pool_manager

        name_check = self._validate_filesystem_name_availability(
            pool_name, fs_name, save_to_db, request_data, must_not_exist=True
        )
        if name_check:
            return name_check

        # ✅ اینجا pool_name را هم پاس می‌دهیم
        quota_check = self._validate_quota_against_pool_capacity(
            pool_manager, pool_name, quota, save_to_db, request_data
        )
        if quota_check:
            return quota_check

        try:
            fs_manager = FilesystemManager()
            fs_manager.create_filesystem(pool_name, fs_name, quota=quota, reservation=reservation, mountpoint=mountpoint)
            return StandardResponse(request_data=request_data, save_to_db=save_to_db,
                                    message=f"فایل‌سیستم '{pool_name}/{fs_name}' با موفقیت ایجاد شد.")
        except Exception as exc:
            return build_standard_error_response(exc=exc, request_data=request_data, save_to_db=save_to_db,
                                                 error_code="filesystem_creation_failed",
                                                 error_message="خطا در ساخت فایل‌سیستم.")

    @extend_schema(parameters=[OpenApiParameter(name="save_to_db", type=bool, required=False, description="ذخیره در دیتابیس")])
    def delete(self, request: Request, pool_name: str, fs_name: str) -> Response:
        """حذف فایل‌سیستم."""
        save_to_db = get_request_param(request, "save_to_db", bool, False)
        request_data = dict(request.data)

        pool_manager = self.validate_zpool_for_operation(pool_name, save_to_db, request_data, must_exist=True)
        if isinstance(pool_manager, StandardErrorResponse):
            return pool_manager

        full_name = f"{pool_name}/{fs_name}"

        name_check = self._validate_filesystem_name_availability(pool_name, fs_name, save_to_db, request_data, must_not_exist=False)
        if name_check:
            return name_check

        fs_manager = FilesystemManager()
        detail = fs_manager.get_filesystem_detail(full_name)
        mountpoint = detail.get("mountpoint") if detail else None

        if mountpoint and mountpoint != "none":
            samba_check = self._is_filesystem_used_in_samba(mountpoint, save_to_db, request_data)
            if samba_check:
                return samba_check

        try:
            fs_manager.destroy_filesystem(full_name)
            return StandardResponse(request_data=request_data, save_to_db=save_to_db,
                                    message=f"فایل‌سیستم '{full_name}' با موفقیت حذف شد.")
        except Exception as exc:
            return build_standard_error_response(exc=exc, request_data=request_data, save_to_db=save_to_db,
                                                 error_code="filesystem_deletion_failed",
                                                 error_message="خطا در حذف فایل‌سیستم.")
