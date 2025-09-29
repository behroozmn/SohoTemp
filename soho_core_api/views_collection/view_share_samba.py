from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.samba import SambaManager
import os


class SambaListView(APIView):
    pass


class SambaCreateView(APIView):
    def post(self, request):
        full_path = request.data.get("full_path", None)
        valid_users = request.data.get("valid_users", "")

        smb = SambaManager()
        path_name = os.path.basename(os.path.normpath(full_path))
        result = smb.add_samba_share_block(share_name=path_name, path=full_path, valid_users=valid_users)

        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


class SambaDeleteView(APIView):
    def delete(self, request):
        share_name = request.data.get("share_name", None)

        smb = SambaManager()
        result = smb.remove_samba_share_block(share_name=share_name)

        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


class SambaListView(APIView):
    def get(self, request):
        smb = SambaManager()
        result = smb.list_shares()

        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


class SambaUserCreateView(APIView):
    """
    POST /api/samba/user/
    Body: { "username": "ali", "password": "mypass123" }
    """

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response({"error": "Both 'username' and 'password' are required."}, status=status.HTTP_400_BAD_REQUEST)
        smb = SambaManager()
        result = smb.create_samba_user(username, password)

        if result["ok"]:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class SambaUserEnableView(APIView):
    """
    POST /api/samba/user/enable/
    Body: { "username": "ali" }
    """

    def post(self, request):
        username = request.data.get("username")
        if not username:
            return Response({"error": "'username' is required."}, status=status.HTTP_400_BAD_REQUEST)
        smb = SambaManager()
        result = smb.enable_samba_user(username)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

class SambaChangePasswordView(APIView):
    """
    POST /api/samba/password/
    Body: { "username": "behrooz", "new_password": "NewSecurePass123!" }
    """
    def post(self, request):
        username = request.data.get("username")
        new_password = request.data.get("new_password")

        if not username or not new_password:
            return Response(
                {"error": "Both 'username' and 'new_password' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        smb = SambaManager()
        result = smb.change_samba_password(username, new_password)

        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)