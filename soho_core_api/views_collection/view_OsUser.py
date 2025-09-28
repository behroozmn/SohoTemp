from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.OSUser import UserManager

class UserListView(APIView):
    def get(self, request):
        manager = UserManager()
        result = manager.list_users()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)