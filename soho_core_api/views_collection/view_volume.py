from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.volume import VolumeManager


class VolumeListView(APIView):
    def get(self, request):
        manager = VolumeManager()
        result = manager.list_volume_detail()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VolumeDetailView(APIView):
    def get(self, request):
        volume_name=request.data.get("volume_name")
        manager = VolumeManager()
        result = manager.list_volume_detail(volume_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)
