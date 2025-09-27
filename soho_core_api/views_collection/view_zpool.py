from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.zpool import ZpoolManager


class ZpoolListView(APIView):
    def get(self, request):
        manager = ZpoolManager()
        result = manager.list_pool_detail()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ZpoolDetailView(APIView):
    def get(self, request, pool_name):
        manager = ZpoolManager()
        result = manager.list_pool_detail(pool_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)


class ZpoolDeleteView(APIView):
    def delete(self, request):
        pool_name = request.data.get("pool_name", "None")
        manager = ZpoolManager()
        result = manager.pool_delete(pool_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ZpoolCreaView(APIView):
    def post(self, request):
        pool_name = request.data.get("pool_name", "None")
        devices = request.data.get("devices", [])
        vdev_type = request.data.get("vdev_type", "None")
        manager = ZpoolManager()
        result = manager.create_pool(pool_name, devices, vdev_type)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
