from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.volume import VolumeManager




class VolumeDetailView(APIView):
    def get(self, request):
        volume_name=request.data.get("volume_name")
        manager = VolumeManager()
        if volume_name:
            result = manager.list_volume_detail(volume_name)
        else:
            result = manager.list_volume_detail()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)
