from xmlrpc.client import boolean

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.OSUser import UserManager


class UserListView(APIView):
    def get(self, request):
        include_system: str = request.data.get("include_system","false")
        manager = UserManager()
        if include_system.lower() in ("true", "1", "yes", "on"):
            result = manager.list_users(include_system=True)
        else:
            result = manager.list_users(include_system=False)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
