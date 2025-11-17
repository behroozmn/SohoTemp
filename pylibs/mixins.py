# soho_core_api/views_collection/mixins.py
from __future__ import annotations

import re
from pylibs import StandardErrorResponse,logger
from pylibs.zpool import ZpoolManager

class ZpoolNameValidationMixin:
    """اعتبارسنجی نام pool ZFS."""
    POOL_NAME_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$'

    def _validate_zpool_name(self, pool_name: str) -> tuple[bool, str | None]:
        if not isinstance(pool_name, str) or not pool_name.strip():
            return False, "نام pool نمی‌تواند خالی باشد."
        if not re.match(self.POOL_NAME_PATTERN, pool_name):
            return False, "نام pool فقط می‌تواند شامل حروف، اعداد، نقطه، زیرخط و خط‌تیره باشد و با حرف/عدد شروع شود."
        if len(pool_name) > 255:
            return False, "نام pool نمی‌تواند بیشتر از 255 کاراکتر باشد."
        return True, None

class ZpoolExistsMixin(ZpoolNameValidationMixin):
    """بررسی وجود pool و اعتبارسنجی آن."""
    def _get_zpool_manager_and_validate(self, pool_name: str, must_exist: bool = True) -> tuple[ZpoolManager | None, str | None]:
        is_valid, error = self._validate_zpool_name(pool_name)
        if not is_valid:
            return None, error
        try:
            manager = ZpoolManager()
            exists = manager.pool_exists(pool_name)
            if must_exist and not exists:
                return None, f"Pool '{pool_name}' وجود ندارد."
            if not must_exist and exists:
                return None, f"Pool '{pool_name}' از قبل وجود دارد."
            return manager, None
        except Exception as e:
            logger.error(f"Error initializing ZpoolManager: {e}")
            return None, "خطا در ایجاد منیجر Zpool."

    def validate_zpool_for_operation(
        self, pool_name: str, save_to_db: bool, request_data: dict, must_exist: bool = True
    ):
        manager, error = self._get_zpool_manager_and_validate(pool_name, must_exist)
        if manager is None:
            status = 404 if "وجود ندارد" in (error or "") else 400
            return StandardErrorResponse(
                error_code="pool_not_found" if must_exist else "pool_already_exists",
                error_message=error or "خطا در اعتبارسنجی pool.",
                request_data=request_data,
                status=status,
                save_to_db=save_to_db
            )
        return manager