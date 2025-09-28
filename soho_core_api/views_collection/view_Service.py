from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.Service import ServiceManager

class ServiceListView(APIView):
    def get(self, request):
        """لیست تمام سرویس‌ها"""
        manager = ServiceManager()
        result = manager.list_services()
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request):
        """عملیات start/stop/restart روی یک سرویس"""
        action = request.data.get("action")
        service = request.data.get("service")

        if not action or not service:
            return Response(
                {"error": "Both 'action' (start/stop/restart) and 'service' are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if action not in ["start", "stop", "restart"]:
            return Response(
                {"error": "Action must be one of: start, stop, restart"},
                status=status.HTTP_400_BAD_REQUEST
            )

        manager = ServiceManager()
        if action == "start":
            result = manager.start_service(service)
        elif action == "stop":
            result = manager.stop_service(service)
        elif action == "restart":
            result = manager.restart_service(service)

        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)