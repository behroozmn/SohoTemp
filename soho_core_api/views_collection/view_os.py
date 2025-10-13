from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from pylibs.sohoOS import SystemManagements

class SystemPowerView(APIView):
    permission_classes = [IsAdminUser]  # فقط ادمین‌ها

    def get(self, request,action):
        if not action:
            return Response("فیلد 'action' الزامی است (مقادیر مجاز: 'shutdown', 'restart').", status=status.HTTP_400_BAD_REQUEST)

        result = SystemManagements.shutdown_or_restart(action.lower()) # shutdown or restart
        status_code = status.HTTP_200_OK if result["ok"] else status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)


class UserListView(APIView):
    def get(self, request):
        manager = SystemManagements()
        result = manager.list_users()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


class UserCreateView(APIView):
    def post(self, request):
        username: str = request.data.get("username")
        login_shell: str = request.data.get("login_shell")
        manager = SystemManagements()
        result = manager.add_user(username, login_shell)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
