from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from pylibs.disk import Disk, DiskManager


@api_view(['GET'])
def disk(myrequest):
    try:
        disk_object = Disk()
        return Response(disk_object.to_dict(), status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status.HTTP_200_OK)


class DiskWwnView(APIView):
    def get(self, request):
        disk_object = Disk()

        result = disk_object.get_disks_wwn_mapping()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DiskFreeView(APIView):
    def get(self, request):
        disk_object = Disk()
        result = disk_object.list_unpartitioned_disks()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DiskDeleteView(APIView):
    def delete(self, request):
        device_name = request.data.get("device_name")
        disk_object = Disk()
        result = disk_object.wipe_disk(device_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DiskListView(APIView):
    def get(self, request):
        dsk = DiskManager()

        # result = dsk.get_disks_all(contain_os_disk=False)

        return Response(dsk.get_disks_all(contain_os_disk=False), status=status.HTTP_200_OK)
