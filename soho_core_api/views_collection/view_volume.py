from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.volume import VolumeManager


class VolumeListView(APIView):
    def get(self, request):
        pass
        volume_manager = VolumeManager()
        result = volume_manager.list_volume_name()
        # if result["ok"]:
        #     return Response(result, status=status.HTTP_200_OK)
        # return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VolumeDetailView(APIView):
    def get(self, request, pool_name):
        pass
        volume_manager = VolumeManager()
        # result = volume_manager.list_pool_details(pool_name)
        # if result["ok"]:
        #     return Response(result, status=status.HTTP_200_OK)
        # return Response(result, status=status.HTTP_404_NOT_FOUND)


class VolumeDeleteView(APIView):
    def delete(self, request):
        pass
        # pool_name = request.data.get("pool_name", "None")
        volume_manager = VolumeManager()
        # result = volume_manager.pool_delete(pool_name)
        # if result["ok"]:
        #     return Response(result, status=status.HTTP_200_OK)
        # return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VolumeCreateView(APIView):
    def post(self, request):
        pass
        pool_name = request.data.get("pool_name", "None")
        devices = request.data.get("devices", [])
        vdev_type = request.data.get("vdev_type", "None")
        volume_manager = VolumeManager()
        # result = volume_manager.create_pool(pool_name,devices, vdev_type)
        # if result["ok"]:
        #     return Response(result, status=status.HTTP_200_OK)
        # return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VolumeDetailView(APIView):
    def get(self, request, pool_name):
        pass
        volume_manager = VolumeManager()
        # result = volume_manager.list_pool_details(pool_name)
        # if result["ok"]:
        #     return Response(result, status=status.HTTP_200_OK)
        # return Response(result, status=status.HTTP_404_NOT_FOUND)
