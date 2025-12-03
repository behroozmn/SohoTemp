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

    def get_samba_users(
            self,
            username: Optional[str] = None,
            *,
            all_props: bool = True,
            property_name: Optional[str] = None,
            only_custom_users: bool = False,
            only_shared_users: bool = False,
    ) -> Union[List[Dict[str, Any]], Dict[str, Any], str, None]:
        try:
            stdout, _ = run_cli_command(["/usr/bin/pdbedit", "-L", "-v"], use_sudo=True)
        except CLICommandError as e:
            logger.error(f"خطا در دریافت لیست کاربران سامبا: {e}")
            raise

        users = self._parse_pdbedit_output(stdout)
        shared_users = self._extract_shared_users_from_conf() if only_shared_users else set()

        # فیلتر اولیه
        filtered_users = []
        for u in users:
            uname = u.get("Unix username")
            if uname is None:
                continue
            if only_shared_users and uname not in shared_users:
                continue
            if only_custom_users and self._is_system_user(uname):
                continue
            filtered_users.append(u)

        if username:
            user = next((u for u in filtered_users if u.get("Unix username") == username), None)
            if user is None:
                return None

            if property_name is not None:
                # 🔑 فقط مقدار پراپرتی خواسته‌شده را برمی‌گرداند
                return user.get(property_name)
            else:
                return user

        else:
            if property_name is not None:
                # برای لیست: فقط آن پراپرتی را از هر کاربر بگیر
                result = []
                for u in filtered_users:
                    uname = u.get("Unix username")
                    val = u.get(property_name)
                    result.append({"Unix username": uname, property_name: val})
                return result
            else:
                return filtered_users

    def get_samba_groups(self, groupname: Optional[str] = None, *, property_name: Optional[str] = None, only_custom_groups: bool = False, only_shared_groups: bool = False, ) -> Union[List[Dict[str, Any]], Dict[str, Any], str, None]:
        """
        دریافت اطلاعات گروه‌های سامبا.
        ساختار مشابه get_samba_users ولی برای گروه‌ها.
        """
        try:
            stdout, _ = run_cli_command(["/usr/bin/getent", "group"], use_sudo=True)
        except CLICommandError as e:
            logger.error(f"خطا در دریافت گروه‌ها: {e}")
            raise

        groups = self._parse_getent_group_output(stdout)
        shared_groups = self._extract_shared_groups_from_conf() if only_shared_groups else set()

        if groupname:
            group = next((g for g in groups if g["name"] == groupname), None)
            if not group:
                return None
            if only_shared_groups and groupname not in shared_groups:
                return None
            if property_name:
                return group.get(property_name)
            return group
        else:
            filtered_groups = []
            for g in groups:
                gname = g["name"]
                if only_shared_groups and gname not in shared_groups:
                    continue
                if only_custom_groups and self._is_system_group(gname):
                    continue
                if property_name:
                    filtered_groups.append({gname: g.get(property_name)})
                else:
                    filtered_groups.append(g)
            return filtered_groups

    def get_samba_sharepoints(self, sharepoint_name: Optional[str] = None, *, property_name: Optional[str] = None, only_custom_shares: bool = False, only_active_shares: bool = False, ) -> Union[List[Dict[str, Any]], Dict[str, Any], str, None]:
        """
        دریافت اطلاعات مسیرهای اشتراکی سامبا از smb.conf.
        """
        shares = self._parse_smb_conf()
        if only_active_shares:
            shares = [s for s in shares if s.get("available", "yes").lower() == "yes"]

        if sharepoint_name:
            share = next((s for s in shares if s["name"] == sharepoint_name), None)
            if not share:
                return None
            if only_custom_shares and not share.get("is_custom", False):
                return None
            if property_name:
                return share.get(property_name)
            return share
        else:
            filtered = []
            for s in shares:
                if only_custom_shares and not s.get("is_custom", False):
                    continue
                if property_name:
                    filtered.append({s["name"]: s.get(property_name)})
                else:
                    filtered.append(s)
            return filtered

    def create_samba_user(self, username: str, password: str, full_name: Optional[str] = None, expiration_date: Optional[str] = None, ) -> None:
        """ایجاد کاربر جدید سامبا."""
        # ایجاد کاربر لینوکس اگر وجود ندارد
        try:
            run_cli_command(["/usr/bin/id", username], use_sudo=True)
        except CLICommandError:
            # کاربر وجود ندارد → ایجاد کن
            cmd = ["/usr/sbin/useradd", "-m", username]
            if full_name:
                cmd.extend(["-c", full_name])
            run_cli_command(cmd, use_sudo=True)

        # تنظیم پسورد سامبا
        run_cli_command(
            ["/usr/bin/smbpasswd", "-a", "-s", username],
            input=f"{password}\n{password}\n",
            use_sudo=True
        )

        # تنظیم تاریخ انقضا
        if expiration_date:
            self.set_user_expiration(username, expiration_date)

    def create_samba_group(self, groupname: str) -> None:
        """ایجاد گروه جدید سامبا."""
        try:
            run_cli_command(["/usr/sbin/groupadd", groupname], use_sudo=True)
        except CLICommandError as e:
            if "already exists" not in str(e):
                raise

    def create_samba_sharepoint(self, name: str, path: str, valid_users: Optional[List[str]] = None, valid_groups: Optional[List[str]] = None, read_only: bool = False, guest_ok: bool = False, browseable: bool = True, max_connections: Optional[int] = None, create_mask: str = "0644", directory_mask: str = "0755", inherit_permissions: bool = False, expiration_time: Optional[str] = None, ) -> None:
        """ایجاد یک مسیر اشتراکی جدید در smb.conf."""
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
            expiration_time=expiration_time
        )

        self._append_share_to_conf(share_section)

    def update_samba_sharepoint(self, name: str, **kwargs: Any) -> None:
        """به‌روزرسانی تمام پراپرتی‌های یک مسیر اشتراکی موجود."""
        shares = self._parse_smb_conf()
        share = next((s for s in shares if s["name"] == name), None)
        if not share:
            raise ValueError(f"مسیر اشتراکی '{name}' یافت نشد.")

        # بروزرسانی مقادیر
        share.update(kwargs)
        new_section = self._build_share_section_from_dict(share)
        self._replace_share_in_conf(name, new_section)

    def change_samba_user_password(self, username: str, new_password: str) -> None:
        """تغییر پسورد کاربر سامبا."""
        run_cli_command(
            ["/usr/bin/smbpasswd", "-s", username],
            input=f"{new_password}\n{new_password}\n",
            use_sudo=True
        )

    def enable_samba_user(self, username: str) -> None:
        """فعال‌سازی کاربر سامبا."""
        run_cli_command(["/usr/bin/smbpasswd", "-e", username], use_sudo=True)

    def disable_samba_user(self, username: str) -> None:
        """غیرفعال‌سازی کاربر سامبا."""
        run_cli_command(["/usr/bin/smbpasswd", "-d", username], use_sudo=True)

    def delete_samba_sharepoint(self, name: str) -> None:
        """حذف یک مسیر اشتراکی از smb.conf."""
        self._remove_share_from_conf(name)

    def delete_samba_user_or_group(self, name: str, is_group: bool = False) -> None:
        """حذف کاربر یا گروه سامبا."""
        if is_group:
            run_cli_command(["/usr/sbin/groupdel", name], use_sudo=True)
        else:
            run_cli_command(["/usr/sbin/userdel", "-r", name], use_sudo=True)
            # حذف از پایگاه سامبا
            try:
                run_cli_command(["/usr/bin/pdbedit", "-x", name], use_sudo=True)
            except CLICommandError:
                pass  # ممکن است از قبل حذف شده باشد

    def set_user_expiration(self, username: str, expiration_date: str) -> None:
        """تعیین تاریخ انقضا برای کاربر."""
        # تاریخ به فرمت YYYY-MM-DD
        from datetime import datetime
        dt = datetime.strptime(expiration_date, "%Y-%m-%d")
        epoch_days = (dt - datetime(1970, 1, 1)).days
        run_cli_command(["/usr/bin/smbpasswd", "-e", "-E", str(epoch_days), username], use_sudo=True)

    def set_group_expiration(self, groupname: str, expiration_date: str) -> None:
        """سامبا از انقضای گروه پشتیبانی نمی‌کند؛ اما می‌توانیم در متادیتای داخلی ذخیره کنیم."""
        raise NotImplementedError("سامبا از انقضای گروه پشتیبانی نمی‌کند.")

    def set_sharepoint_expiration(self, sharepoint_name: str, expiration_time: str) -> None:
        """تعیین زمان انقضا برای مسیر اشتراکی (معمولًا در کامنت ذخیره می‌شود)."""
        self.update_samba_sharepoint(sharepoint_name, expiration_time=expiration_time)

    # ----------------------------
    # Internal Helper Methods
    # ----------------------------

    def _parse_pdbedit_output(self, output: str) -> List[Dict[str, str]]:
        users = []
        current = {}
        for line in output.strip().split("\n"):
            if line.strip() == "":
                if current:
                    users.append(current)
                    current = {}
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                current[key.strip()] = val.strip()
        if current:
            users.append(current)
        return users

    def _parse_getent_group_output(self, output: str) -> List[Dict[str, Any]]:
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
        if not os.path.exists(self.SMB_CONF_PATH):
            return []
        with open(self.SMB_CONF_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # پیدا کردن بخش SOHO
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

            # اضافه کردن expiration اگر وجود داشته باشد (در کامنت)
            exp_match = re.search(r"#Expiration:\s*(\S+)", section_body)
            if exp_match:
                props["expiration_time"] = exp_match.group(1)

            shares.append(props)
        return shares

    def _extract_shared_users_from_conf(self) -> set:
        users = set()
        shares = self._parse_smb_conf()
        for s in shares:
            vu = s.get("valid users", "")
            if vu:
                users.update(u.strip() for u in vu.split(",") if u.strip())
        return users

    def _extract_shared_groups_from_conf(self) -> set:
        groups = set()
        shares = self._parse_smb_conf()
        for s in shares:
            vg = s.get("valid groups", "")
            if vg:
                groups.update(g.strip() for g in vg.split(",") if g.strip())
        return groups

    def _is_system_user(self, username: str) -> bool:
        try:
            stdout, _ = run_cli_command(["/usr/bin/id", "-u", username], use_sudo=True)
            uid = int(stdout.strip())
            return uid < 1000  # معمولاً UID < 1000 برای سیستم
        except:
            return True

    def _is_system_group(self, groupname: str) -> bool:
        try:
            stdout, _ = run_cli_command(["/usr/bin/getent", "group", groupname], use_sudo=True)
            gid = int(stdout.strip().split(":")[2])
            return gid < 1000
        except:
            return True

    def _build_share_section(self, name: str, path: str, valid_users: Optional[List[str]], valid_groups: Optional[List[str]], read_only: bool, guest_ok: bool, browseable: bool, max_connections: Optional[int], create_mask: str, directory_mask: str, inherit_permissions: bool, expiration_time: Optional[str], ) -> str:
        section = f"#Begin: {name}\n[{name}]\n"
        section += f"path = {path}\n"
        section += f"create mask = {create_mask}\n"
        section += f"directory mask = {directory_mask}\n"
        if max_connections is not None:
            section += f"max connections = {max_connections}\n"
        section += f"read only = {'yes' if read_only else 'no'}\n"
        section += f"available = yes\n"
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
        )

    def _append_share_to_conf(self, section: str) -> None:
        with open(self.SMB_CONF_PATH, "r+", encoding="utf-8") as f:
            content = f.read()
            if self.SOHO_SECTION_MARKER not in content:
                content += f"\n\n{self.SOHO_SECTION_MARKER}\n\n"
            f.seek(0)
            f.write(content.rstrip() + "\n" + section)
        self._reload_samba()

    def _replace_share_in_conf(self, name: str, new_section: str) -> None:
        with open(self.SMB_CONF_PATH, "r+", encoding="utf-8") as f:
            content = f.read()
            pattern = rf"#Begin: {re.escape(name)}[\s\S]*?#End: {re.escape(name)}.*?\n\n?"
            new_content = re.sub(pattern, new_section, content, flags=re.MULTILINE)
            f.seek(0)
            f.write(new_content)
            f.truncate()
        self._reload_samba()

    def _remove_share_from_conf(self, name: str) -> None:
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
        user = self.get_samba_users(username=username)
        if user and isinstance(user, dict):
            return user.get(prop_key)
        return None

    def get_samba_group_property(self, groupname: str, prop_key: str) -> Optional[str]:
        group = self.get_samba_groups(groupname=groupname)
        if group and isinstance(group, dict):
            return group.get(prop_key)
        return None

    def get_samba_sharepoint_property(self, name: str, prop_key: str) -> Optional[str]:
        share = self.get_samba_sharepoints(sharepoint_name=name)
        if share and isinstance(share, dict):
            return share.get(prop_key)
        return None