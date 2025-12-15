#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
from typing import Any, Dict, Optional
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

def ok(data: Any, details: Any = None) -> Dict[str, Any]:
    return {
        "ok": True,
        "error": None,
        "data": data,
        "details": details or {}
    }


def fail(message: str, code: str = "service_error", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": {"code": code, "message": message, "extra": extra or {}},
        "data": None,
        "details": {}
    }



class WebManager:
    """
    Django User Management Utility
    Works with Django's built-in User model.
    All methods return standardized ok/fail responses.
    """

    @staticmethod
    def create_user(username: str, email: str, password: str, is_superuser: bool = False, first_name: str = "", last_name: str = "") -> Dict[str, Any]:
        """
        Create a new Django user (superuser or regular).
        Endpoint: POST /api/users/create/
        """
        if not username or not password:
            return fail("Username and password are required.", "missing_fields")

        if User.objects.filter(username=username).exists():
            return fail(f"User '{username}' already exists.", "user_exists")

        try:
            validate_password(password)
        except ValidationError as e:
            return fail("Password validation failed.", "invalid_password", {"errors": list(e.messages)})

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                if is_superuser:
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()

            return ok({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_superuser": user.is_superuser,
                "created_at": user.date_joined.isoformat()
            }, {"message": "User created successfully."})

        except Exception as e:
            return fail(f"Failed to create user: {str(e)}", "creation_failed")

    @staticmethod
    def delete_user(username: str, delete_from_db: bool = True) -> Dict[str, Any]:
        """
        Delete a Django user by username.
        Endpoint: DELETE /api/users/{username}/
        """
        try:
            user = User.objects.get(username=username)
            user_id = user.id
            user.delete()
            return ok({
                "deleted_user_id": user_id,
                "username": username
            }, {"message": f"User '{username}' deleted successfully."})
        except User.DoesNotExist:
            return fail(f"User '{username}' does not exist.", "user_not_found")
        except Exception as e:
            return fail(f"Failed to delete user: {str(e)}", "deletion_failed")

    @staticmethod
    def change_password(username: str, new_password: str) -> Dict[str, Any]:
        """
        Change password for an existing Django user.
        Endpoint: PATCH /api/users/{username}/change-password/
        """
        if not new_password:
            return fail("New password is required.", "missing_password")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return fail(f"User '{username}' does not exist.", "user_not_found")

        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            return fail("Password validation failed.", "invalid_password", {"errors": list(e.messages)})

        try:
            user.set_password(new_password)
            user.save()
            return ok({
                "username": username
            }, {"message": "Password updated successfully."})
        except Exception as e:
            return fail(f"Failed to update password: {str(e)}", "password_update_failed")

    @staticmethod
    def list_users() -> Dict[str, Any]:
        """
        List all Django users with full details.
        Endpoint: GET /api/users/
        """
        try:
            users = User.objects.all().order_by('id')
            data = [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "is_active": u.is_active,
                    "is_staff": u.is_staff,
                    "is_superuser": u.is_superuser,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "date_joined": u.date_joined.isoformat(),
                }
                for u in users
            ]
            return ok(data, {"count": len(data)})
        except Exception as e:
            return fail(f"Failed to fetch users: {str(e)}", "list_failed")
