from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.zpool import ZpoolManager


class ZpoolListNameView(APIView):
    def get(self, request):
        manager = ZpoolManager()
        result = manager.list_pools_name()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ZpoolListDetailView(APIView):
    def post(self, request):
        name = request.data.get("pool_name", "None")
        manager = ZpoolManager()
        result = manager.list_pool_details(name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)
