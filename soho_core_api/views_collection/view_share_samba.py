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
    def post(self, request):
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
