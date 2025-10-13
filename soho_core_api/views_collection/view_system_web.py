from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from pylibs.sohoSystem import WebManager


class WebUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        result = WebManager.list_users()
        if result["ok"]:
            return Response(result["data"])
        return Response(result["error"], status=500)


class WebUserCreateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        is_superuser = request.data.get("is_superuser", False)
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")

        result = WebManager.create_user(
            username=username,
            email=email,
            password=password,
            is_superuser=is_superuser,
            first_name=first_name,
            last_name=last_name
        )
        if result["ok"]:
            return Response(result["data"], status=status.HTTP_201_CREATED)
        return Response(result["error"], status=status.HTTP_400_BAD_REQUEST)


class WebUserDeleteView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, username):
        result = WebManager.delete_user(username)
        if result["ok"]:
            return Response(result["data"])
        return Response(result["error"], status=404 if "not found" in result["error"]["message"].lower() else 400)


class WebUserChangePasswordView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, username):
        new_password = request.data.get("new_password")
        if not new_password:
            return Response({"error": "new_password is required"}, status=400)

        result = WebManager.change_password(username, new_password)
        if result["ok"]:
            return Response(result["data"])
        return Response(result["error"], status=400)
