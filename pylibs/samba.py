# soho_core_api/pylibs/samba.py
from __future__ import annotations
import os
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pylibs import logger, CLICommandError, run_cli_command


class SambaManager:
    """
    مدیریت کامل کاربران، گروه‌ها و مسیرهای اشتراکی سرویس Samba.
    تمام توابع فقط داده خام (Dict, List, str, None) یا استثنا برمی‌گردانند.
    """
    SMB_CONF_PATH = "/etc/samba/smb.conf"
    SOHO_SECTION_MARKER = "## SOHO Configurations ##"

    def __init__(self) -> None:
        pass

    def get_samba_users(self, username: Optional[str] = None, *, property_name: Optional[str] = None, ) -> Union[List[Dict[str, Any]], Dict[str, Any], str, None]:
        """
        دریافت اطلاعات کاربران سامبا.

        Args:
            username: نام کاربر خاص. اگر None باشد، تمام کاربران برگردانده می‌شوند.
            property_name: نام یک پراپرتی خاص برای بازیابی (مثلاً "Logoff time").
                           اگر None باشد، تمام پراپرتی‌ها برگردانده می‌شوند.

        Returns:
            - dict: اگر username مشخص باشد و کاربر یافت شود.
            - list[dict]: اگر username داده نشده باشد.
            - str: اگر property_name مشخص باشد و فقط یک مقدار بازگردانده شود.
            - None: اگر کاربر یافت نشود.

        Raises:
            CLICommandError: در صورت خطا در اجرای دستور CLI (مثل pdbedit).
        """
        try:
            stdout, _ = run_cli_command(["/usr/bin/pdbedit", "-L", "-v"], use_sudo=True)
        except CLICommandError as e:
            logger.error(f"خطا در دریافت لیست کاربران سامبا: {e}")
            raise

        users = self._parse_pdbedit_output(stdout)

        if username:
            user = next((u for u in users if u.get("Unix username") == username), None)
            if user is None:
                return None
            if property_name is not None:
                return user.get(property_name)
            else:
                return user
        else:
            if property_name is not None:
                result = []
                for u in users:
                    uname = u.get("Unix username")
                    val = u.get(property_name)
                    result.append({"Unix username": uname, property_name: val})
                return result
            else:
                return users

    def get_samba_groups(self, groupname: Optional[str] = None, *, property_name: Optional[str] = None, contain_system_groups: bool = True, ) -> Union[List[Dict[str, Any]], Dict[str, Any], str, None]:
        """
        دریافت اطلاعات گروه‌های سامبا.

        Args:
            groupname: نام گروه خاص. اگر None باشد، تمام گروه‌ها برگردانده می‌شوند.
            property_name: نام یک پراپرتی خاص برای بازیابی.
            contain_system_groups: اگر True باشد، همه گروه‌ها (شامل سیستمی) برگردانده می‌شوند.
                                   اگر False باشد، فقط گروه‌های کاربری (GID >= 1000) برگردانده می‌شوند.
                                   گروه 'nogroup' همیشه به عنوان گروه سیستمی در نظر گرفته می‌شود.

        Returns:
            - dict: اگر groupname مشخص باشد و گروه یافت شود.
            - list[dict]: اگر groupname داده نشده باشد.
            - str: اگر property_name مشخص باشد و فقط یک مقدار بازگردانده شود.
            - None: اگر گروه یافت نشود.

        Raises:
            CLICommandError: در صورت خطا در اجرای دستور `getent group`.
        """
        try:
            stdout, _ = run_cli_command(["/usr/bin/getent", "group"], use_sudo=True)
        except CLICommandError as e:
            logger.error(f"خطا در دریافت گروه‌ها: {e}")
            raise

        groups = self._parse_getent_group_output(stdout)

        # فیلتر گروه‌های غیرسیستمی (اگر درخواست شده باشد)
        if not contain_system_groups:
            filtered_groups = []
            for g in groups:
                gname = g.get("name")
                gid_str = g.get("gid")

                if gname == "nogroup":  continue  # گروه nogroup همیشه سیستمی است

                # گروههای زیر طبق قاعده در زمره سیستمی قرار گرفته است
                if gname == "smbadmin" or gname == "smbgroup" or gname == "smbuser" or gname == "system" or gname == "user":
                    continue
                try:
                    gid = int(gid_str) if gid_str is not None else -1
                    if gid >= 1000:
                        filtered_groups.append(g)
                except (ValueError, TypeError):
                    # اگر GID نامعتبر بود، به عنوان سیستمی در نظر بگیر
                    continue
            groups = filtered_groups

        if groupname:
            group = next((g for g in groups if g["name"] == groupname), None)
            if not group:
                return None
            if property_name:
                return group.get(property_name)
            return group
        else:
            if property_name:
                return [{g["name"]: g.get(property_name)} for g in groups]
            else:
                return groups

    def get_samba_sharepoints(self, sharepoint_name: Optional[str] = None, *, property_name: Optional[str] = None, only_active_shares: bool = False, ) -> Union[List[Dict[str, Any]], Dict[str, Any], str, None]:
        """
        دریافت اطلاعات مسیرهای اشتراکی سامبا از smb.conf.

        Args:
            sharepoint_name: نام مسیر اشتراکی خاص. اگر None باشد، تمام مسیرها برگردانده می‌شوند.
            property_name: نام یک پراپرتی خاص برای بازیابی.
            only_active_shares: اگر True باشد، فقط مسیرهایی که available=yes هستند.

        Returns:
            - dict: اگر sharepoint_name مشخص باشد و مسیر یافت شود.
            - list[dict]: اگر sharepoint_name داده نشده باشد.
            - str: اگر property_name مشخص باشد و فقط یک مقدار بازگردانده شود.
            - None: اگر مسیر یافت نشود.

        Raises:
            FileNotFoundError, IOError: در صورتی که دسترسی به فایل smb.conf با مشکل مواجه شود.
        """
        shares = self._parse_smb_conf()
        if only_active_shares:
            shares = [s for s in shares if s.get("available", "yes").lower() == "yes"]

        if sharepoint_name:
            share = next((s for s in shares if s["name"] == sharepoint_name), None)
            if not share:
                return None
            if property_name:
                return share.get(property_name)
            return share
        else:
            if property_name:
                return [{s["name"]: s.get(property_name)} for s in shares]
            else:
                return shares

    def create_samba_user(self, username: str, password: str, full_name: Optional[str] = None, expiration_date: Optional[str] = None) -> None:
        """
        ایجاد یک کاربر جدید سامبا با مدیریت هوشمند گروه‌های هم‌نام.
        """
        # بررسی وجود گروه با نام کاربر
        group_exists = False
        try:
            run_cli_command(["/usr/bin/getent", "group", username], use_sudo=True)
            group_exists = True
        except CLICommandError:
            # گروه یافت نشد → ایجاد خودکار توسط useradd مجاز است
            pass

        # ساخت کاربر
        cmd = ["/usr/sbin/useradd", "-m"]
        if group_exists:
            # اگر گروه وجود دارد، کاربر را به آن اضافه کن
            cmd.extend(["-g", username])
        if full_name:
            cmd.extend(["-c", full_name])
        cmd.append(username)

        try:
            run_cli_command(cmd, use_sudo=True)
        except CLICommandError as e:
            if "already exists" in str(e):
                # کاربر از قبل وجود دارد → ادامه بده (برای smbpasswd)
                pass
            else:
                raise

        # تنظیم رمز عبور سامبا
        run_cli_command(
            ["/usr/bin/smbpasswd", "-a", "-s", username],
            input=f"{password}\n{password}\n",
            use_sudo=True
        )

        # تنظیم تاریخ انقضا (در صورت نیاز)
        if expiration_date:
            self.set_user_expiration(username, expiration_date)

    def create_samba_group(self, groupname: str) -> None:
        """
        ایجاد یک گروه جدید سامبا.

        Args:
            groupname: نام گروه یونیکس (کوچک، بدون فاصله).

        Raises:
            CLICommandError: در صورت خطا در ایجاد گروه.
        """
        try:
            run_cli_command(["/usr/sbin/groupadd", groupname], use_sudo=True)
        except CLICommandError as e:
            if "already exists" not in str(e):
                raise

    def create_samba_sharepoint(self, name: str, path: str, valid_users: Optional[List[str]] = None, valid_groups: Optional[List[str]] = None, read_only: bool = False, guest_ok: bool = False, browseable: bool = True, max_connections: Optional[int] = None, create_mask: str = "0644", directory_mask: str = "0755", inherit_permissions: bool = False, expiration_time: Optional[str] = None, available: bool = True,) -> None:
        """
        ایجاد یک مسیر اشتراکی جدید در فایل smb.conf.

        Args:
            name: نام منحصر به فرد مسیر اشتراکی.
            path: مسیر فیزیکی در سیستم فایل.
            valid_users: لیست کاربران مجاز (اختیاری).
            valid_groups: لیست گروه‌های مجاز (اختیاری).
            read_only: اگر True باشد، فقط خواندنی است.
            guest_ok: اگر True باشد، دسترسی مهمان فعال است.
            browseable: اگر True باشد، در لیست‌های اشتراک قابل مشاهده است.
            available: دردسترس
            max_connections: حداکثر تعداد اتصال همزمان (اختیاری).
            create_mask: ماسک دسترسی فایل‌های جدید (پیش‌فرض: "0644").
            directory_mask: ماسک دسترسی دایرکتوری‌های جدید (پیش‌فرض: "0755").
            inherit_permissions: ارث‌بری دسترسی‌ها از والد (اختیاری).
            expiration_time: زمان انقضا (اختیاری، در کامنت ذخیره می‌شود).
            available: اگر True باشد، مسیر اشتراکی فعال است (پیش‌فرض: True).


        Raises:
            OSError, IOError: در صورت خطا در دسترسی به smb.conf یا ایجاد مسیر فیزیکی.
        """
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            run_cli_command(["/usr/bin/chown", "root:root", path], use_sudo=True)

        share_section = self._build_share_section(
            name=name,
            path=path,
            valid_users=valid_users,
            valid_groups=valid_groups,
            read_only=read_only,
            guest_ok=guest_ok,
            browseable=browseable,
            max_connections=max_connections,
            create_mask=create_mask,
            directory_mask=directory_mask,
            inherit_permissions=inherit_permissions,
            expiration_time=expiration_time,
            available=available,
        )

        self._append_share_to_conf(share_section)

    def update_samba_sharepoint(self, name: str, **kwargs: Any) -> None:
        """
        به‌روزرسانی تمام پراپرتی‌های یک مسیر اشتراکی موجود.

        Args:
            name: نام مسیر اشتراکی موجود.
            **kwargs: پراپرتی‌های جدید برای بروزرسانی.

        Raises:
            ValueError: اگر مسیر اشتراکی یافت نشود.
            OSError, IOError: در صورت خطا در دسترسی به smb.conf.
        """
        shares = self._parse_smb_conf()
        share = next((s for s in shares if s["name"] == name), None)
        print(f"shares:{shares}")
        print(f"share:{share}")
        if not share:
            raise ValueError(f"مسیر اشتراکی '{name}' یافت نشد.")

        # ✅ پردازش مقادیر ورودی
        processed_kwargs = {}
        # print(f"kwargs:{kwargs}")
        for key, value in kwargs.items():
            # --- 1. تبدیل لیست‌ها به رشته
            if key == "valid users" and isinstance(value, list):
                processed_kwargs[key] = ", ".join(str(v) for v in value)
            elif key == "valid groups" and isinstance(value, list):
                processed_kwargs[key] = ", ".join(str(v) for v in value)
            # --- 2. تبدیل مقادیر بولین به رشته
            elif key in ("read only", "guest ok", "browseable", "inherit permissions", "available"):
                if isinstance(value, bool):
                    processed_kwargs[key] = "yes" if value else "no"
                elif isinstance(value, str):
                    processed_kwargs[key] = value.lower()
                else:
                    # در صورت غیر bool یا str، فرض کن "no"
                    processed_kwargs[key] = "no"
            # --- 3. بقیه مقادیر بدون تغییر
            else:
                processed_kwargs[key] = value

        share.update(processed_kwargs)
        new_section = self._build_share_section_from_dict(share)
        self._replace_share_in_conf(name, new_section)

    def change_samba_user_password(self, username: str, new_password: str) -> None:
        """
        تغییر رمز عبور یک کاربر سامبا.

        Args:
            username: نام کاربر.
            new_password: رمز عبور جدید.

        Raises:
            CLICommandError: در صورت خطا در تغییر رمز.
        """
        run_cli_command(["/usr/bin/smbpasswd", "-s", username], input=f"{new_password}\n{new_password}\n", use_sudo=True)

    def enable_samba_user(self, username: str) -> None:
        """
        فعال‌سازی یک کاربر سامبا.

        Args:
            username: نام کاربر.

        Raises:
            CLICommandError: در صورت خطا در فعال‌سازی.
        """
        run_cli_command(["/usr/bin/smbpasswd", "-e", username], use_sudo=True)

    def disable_samba_user(self, username: str) -> None:
        """
        غیرفعال‌سازی یک کاربر سامبا.

        Args:
            username: نام کاربر.

        Raises:
            CLICommandError: در صورت خطا در غیرفعال‌سازی.
        """
        run_cli_command(["/usr/bin/smbpasswd", "-d", username], use_sudo=True)

    def delete_samba_sharepoint(self, name: str) -> None:
        """
        حذف یک مسیر اشتراکی از smb.conf.

        Args:
            name: نام مسیر اشتراکی.

        Raises:
            OSError, IOError: در صورت خطا در دسترسی به smb.conf.
        """
        self._remove_share_from_conf(name)

    def delete_samba_user_from_system(self, username: str) -> None:
        """
        حذف کاربر از سیستم عامل لینوکس (همراه با home directory).

        Args:
            username: نام کاربر لینوکس.

        Raises:
            CLICommandError: در صورت خطا در اجرای دستور userdel.
        """
        cmd = ["/usr/sbin/userdel", "-r", username]
        run_cli_command(cmd, use_sudo=True)

    def delete_samba_user_from_samba_db(self, username: str) -> None:
        """
        حذف کاربر از پایگاه داده سامبا (pdbedit).

        Args:
            username: نام کاربر سامبا.

        Raises:
            CLICommandError: در صورت خطا در اجرای دستور pdbedit -x.
        """
        cmd = ["/usr/bin/pdbedit", "-x", username]
        run_cli_command(cmd, use_sudo=True)

    def delete_samba_group(self, groupname: str) -> None:
        """
        حذف یک گروه سامبا از سیستم.

        Args:
            groupname: نام گروه سامبا.

        Raises:
            CLICommandError: در صورت خطا در حذف گروه.
        """
        run_cli_command(["/usr/sbin/groupdel", groupname], use_sudo=True)

    def set_user_expiration(self, username: str, expiration_date: str) -> None:
        """
        تعیین تاریخ انقضا برای کاربر.

        Args:
            username: نام کاربر.
            expiration_date: تاریخ به فرمت "YYYY-MM-DD".

        Raises:
            ValueError: اگر فرمت تاریخ نامعتبر باشد.
            CLICommandError: در صورت خطا در تنظیم انقضا.
        """
        dt = datetime.strptime(expiration_date, "%Y-%m-%d")
        epoch_days = (dt - datetime(1970, 1, 1)).days
        run_cli_command(["/usr/bin/smbpasswd", "-e", "-E", str(epoch_days), username], use_sudo=True)

    def set_sharepoint_expiration(self, sharepoint_name: str, expiration_time: str) -> None:
        """
        تعیین زمان انقضا برای مسیر اشتراکی (در کامنت smb.conf).

        Args:
            sharepoint_name: نام مسیر اشتراکی.
            expiration_time: زمان انقضا (هر فرمت رشته‌ای قابل قبول است).
        """
        self.update_samba_sharepoint(sharepoint_name, expiration_time=expiration_time)

    # ----------------------------
    # Internal Helper Methods
    # ----------------------------

    def _parse_pdbedit_output(self, output: str) -> List[Dict[str, str]]:
        """
        تجزیه خروجی دستور `pdbedit -L -v` که از '---------------' برای جداکردن کاربران استفاده می‌کند.

        Args:
            output: خروجی خام دستور pdbedit.

        Returns:
            لیستی از دیکشنری‌های حاوی جزئیات هر کاربر.
        """
        users = []
        current = {}
        lines = output.strip().split("\n")

        for line in lines:
            stripped = line.strip()
            if stripped == "---------------":
                if current:
                    users.append(current)
                    current = {}
                continue

            if not stripped or ": " not in stripped:
                continue

            key, val = stripped.split(": ", 1)
            key = key.strip()
            val = val.strip()
            current[key] = val

        if current:
            users.append(current)

        return users

    def _parse_getent_group_output(self, output: str) -> List[Dict[str, Any]]:
        """تجزیه خروجی دستور `getent group` به لیست گروه‌ها."""
        groups = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                groups.append({
                    "name": parts[0],
                    "gid": parts[2],
                    "members": parts[3].split(",") if parts[3] else []
                })
        return groups

    def _parse_smb_conf(self) -> List[Dict[str, Any]]:
        """خواندن و تجزیه فایل smb.conf برای استخراج مسیرهای اشتراکی."""
        if not os.path.exists(self.SMB_CONF_PATH):
            return []
        with open(self.SMB_CONF_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        if self.SOHO_SECTION_MARKER not in content:
            return []

        soho_start = content.find(self.SOHO_SECTION_MARKER)
        soho_part = content[soho_start:]

        shares = []
        pattern = r"#Begin: ([^\n]+)\n\[([^\]]+)\]([\s\S]*?)#End: \2.*?(\d{4}/\d{2}/\d{2}-\d{2}:\d{2}:\d{2})?"
        for match in re.finditer(pattern, soho_part):
            name = match.group(1).strip()
            section_body = match.group(3)
            created_time = match.group(4)

            props = {"name": name, "is_custom": True, "created_time": created_time}
            for line in section_body.strip().split("\n"):
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip()

            exp_match = re.search(r"#Expiration:\s*(\S+)", section_body)
            if exp_match:
                props["expiration_time"] = exp_match.group(1)

            shares.append(props)
        return shares

    def _build_share_section(self, name: str, path: str, valid_users: Optional[List[str]], valid_groups: Optional[List[str]], read_only: bool, guest_ok: bool, browseable: bool, max_connections: Optional[int], create_mask: str, directory_mask: str, inherit_permissions: bool, expiration_time: Optional[str], available: bool = True,) -> str:
        """ساخت بخش متنی یک مسیر اشتراکی برای افزودن به smb.conf."""
        section = f"#Begin: {name}\n[{name}]\n"
        section += f"path = {path}\n"
        section += f"create mask = {create_mask}\n"
        section += f"directory mask = {directory_mask}\n"
        if max_connections is not None:
            section += f"max connections = {max_connections}\n"
        section += f"read only = {'yes' if read_only else 'no'}\n"
        section += f"available = {'yes' if available else 'no'}\n"  # ← فقط این خط
        section += f"guest ok = {'yes' if guest_ok else 'no'}\n"
        section += f"browseable = {'yes' if browseable else 'no'}\n"
        section += f"inherit permissions = {'yes' if inherit_permissions else 'no'}\n"
        if valid_users:
            section += f"valid users = {', '.join(valid_users)}\n"
        if valid_groups:
            section += f"valid groups = {', '.join(valid_groups)}\n"
        if expiration_time:
            section += f"#Expiration: {expiration_time}\n"
        current_time = datetime.now().strftime("%Y/%m/%d-%H:%M:%S")
        section += f"#End: {name} - CreatedTime: {current_time}\n\n"
        return section

    def _build_share_section_from_dict(self, share: Dict[str, Any]) -> str:
        """ساخت بخش متنی بر اساس دیکشنری موجود (برای به‌روزرسانی)."""
        return self._build_share_section(
            name=share["name"],
            path=share.get("path", ""),
            valid_users=[u.strip() for u in share.get("valid users", "").split(",")] if share.get("valid users") else None,
            valid_groups=[g.strip() for g in share.get("valid groups", "").split(",")] if share.get("valid groups") else None,
            read_only=share.get("read only", "no").lower() == "yes",
            guest_ok=share.get("guest ok", "no").lower() == "yes",
            browseable=share.get("browseable", "yes").lower() == "yes",
            max_connections=int(share["max connections"]) if share.get("max connections") else None,
            create_mask=share.get("create mask", "0644"),
            directory_mask=share.get("directory mask", "0755"),
            inherit_permissions=share.get("inherit permissions", "no").lower() == "yes",
            expiration_time=share.get("expiration_time"),
            available=share.get("available", "yes").lower() == "yes",
        )

    def _append_share_to_conf(self, section: str) -> None:
        """افزودن یک مسیر اشتراکی به انتهای smb.conf."""
        with open(self.SMB_CONF_PATH, "r+", encoding="utf-8") as f:
            content = f.read()
            if self.SOHO_SECTION_MARKER not in content:
                content += f"\n\n{self.SOHO_SECTION_MARKER}\n\n"
            f.seek(0)
            f.write(content.rstrip() + "\n" + section)
        self._reload_samba()

    def _replace_share_in_conf(self, name: str, new_section: str) -> None:
        """جایگزینی یک مسیر اشتراکی موجود در smb.conf."""
        with open(self.SMB_CONF_PATH, "r+", encoding="utf-8") as f:
            content = f.read()
            pattern = rf"#Begin: {re.escape(name)}[\s\S]*?#End: {re.escape(name)}.*?\n\n?"
            new_content = re.sub(pattern, new_section, content, flags=re.MULTILINE)
            f.seek(0)
            f.write(new_content)
            f.truncate()
        self._reload_samba()

    def _remove_share_from_conf(self, name: str) -> None:
        """حذف یک مسیر اشتراکی از smb.conf."""
        with open(self.SMB_CONF_PATH, "r+", encoding="utf-8") as f:
            content = f.read()
            pattern = rf"#Begin: {re.escape(name)}[\s\S]*?#End: {re.escape(name)}.*?\n\n?"
            new_content = re.sub(pattern, "", content, flags=re.MULTILINE)
            f.seek(0)
            f.write(new_content)
            f.truncate()
        self._reload_samba()

    def _reload_samba(self) -> None:
        """ریلود سرویس سامبا برای اعمال تغییرات."""
        try:
            run_cli_command(["/usr/bin/sudo", "/usr/sbin/service", "smbd", "reload"], use_sudo=False)
        except CLICommandError:
            run_cli_command(["/usr/bin/sudo", "/bin/systemctl", "reload", "smbd"], use_sudo=False)

    def get_samba_user_property(self, username: str, prop_key: str) -> Optional[str]:
        """دریافت مقدار یک پراپرتی خاص از یک کاربر سامبا."""
        user = self.get_samba_users(username=username)
        if user and isinstance(user, dict):
            return user.get(prop_key)
        return None

    def get_samba_group_property(self, groupname: str, prop_key: str) -> Optional[str]:
        """دریافت مقدار یک پراپرتی خاص از یک گروه سامبا."""
        group = self.get_samba_groups(groupname=groupname)
        if group and isinstance(group, dict):
            return group.get(prop_key)
        return None

    def get_samba_sharepoint_property(self, name: str, prop_key: str) -> Optional[str]:
        """دریافت مقدار یک پراپرتی خاص از یک مسیر اشتراکی سامبا."""
        share = self.get_samba_sharepoints(sharepoint_name=name)
        if share and isinstance(share, dict):
            return share.get(prop_key)
        return None

    def _is_system_group(self, groupname: str) -> bool:
        """بررسی اینکه آیا گروه یک گروه سیستمی است یا خیر."""
        try:
            stdout, _ = run_cli_command(["/usr/bin/getent", "group", groupname], use_sudo=True)
            if not stdout.strip():
                return True  # گروه وجود ندارد → سیستمی در نظر گرفته شود
            parts = stdout.strip().split(":")
            if len(parts) >= 3:
                gid = int(parts[2])
                return gid < 1000
            return True
        except (ValueError, IndexError, CLICommandError):
            return True

    def add_user_to_group(self, username: str, groupname: str) -> None:
        """
        افزودن یک کاربر به یک گروه سامبا.

        Args:
            username: نام کاربر.
            groupname: نام گروه.

        Raises:
            CLICommandError: در صورت خطا در اجرای دستور usermod.
        """
        cmd = ["/usr/sbin/usermod", "-a", "-G", groupname, username]
        run_cli_command(cmd, use_sudo=True)

    def remove_user_from_group(self, username: str, groupname: str) -> None:
        """
        حذف یک کاربر از یک گروه سامبا.

        Args:
            username: نام کاربر.
            groupname: نام گروه.

        Raises:
            CLICommandError: در صورت خطا در اجرای دستور gpasswd.
        """
        cmd = ["/usr/bin/gpasswd", "-d", username, groupname]
        run_cli_command(cmd, use_sudo=True)
