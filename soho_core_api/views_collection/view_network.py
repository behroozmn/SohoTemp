from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser  # فقط ادمین‌ها
from rest_framework import status

from pylibs.networkmanager import NetworkManager


@api_view(['GET'])
def network(request):
    try:
        net = NetworkManager()
        return Response(net.to_dict(), status.HTTP_200_OK)
    except RuntimeError as e:
        return Response({"error": str(e)}, status.HTTP_200_OK)


class GetAllNetworkInterfacesView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        result = NetworkManager.get_all_interfaces_config()
        status_code = status.HTTP_200_OK if result["ok"] else status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)


class GetNetworkInterfaceView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, interface_name):
        result = NetworkManager.get_interface_config(interface_name)
        status_code = status.HTTP_200_OK if result["ok"] else status.HTTP_404_NOT_FOUND
        return Response(result, status=status_code)


class UpdateNetworkInterfaceIPView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, interface_name):
        ip = request.data.get("ip")
        netmask = request.data.get("netmask")

        if not all([interface_name, ip, netmask]):
            return Response({"Message": "فیلدهای interface, ip و netmask الزامی هستند."}, status=status.HTTP_400_BAD_REQUEST)
        net = NetworkManager()
        result = net.update_interface_ip(interface_name, ip, netmask)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
