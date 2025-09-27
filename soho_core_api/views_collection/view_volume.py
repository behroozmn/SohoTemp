from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.volume import VolumeManager


class VolumeDetailView(APIView):
    def get(self, request):
        volume_name = request.data.get("volume_name")
        zfs_manager = VolumeManager()
        if volume_name:
            result = zfs_manager.list_volume_detail(volume_name)
        else:
            result = zfs_manager.list_volume_detail()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)


class VolumeCreateView(APIView):
    def post(self, request):
        volume_name = request.data.get("volume_name", "None")
        volsize = request.data.get("volsize", "100G")
        zfs_manager = VolumeManager()
        result = zfs_manager.create(volume_name, {"volsize": volsize})
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
