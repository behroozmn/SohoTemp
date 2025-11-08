from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from pylibs.disktemp import DiskTemp, DiskManager


@api_view(['GET'])
def disk(myrequest):
    try:
        disk_object = DiskTemp()
        return Response(disk_object.to_dict(), status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status.HTTP_200_OK)


class DiskWwnView(APIView):
    def get(self, request):
        disk_object = DiskTemp()

        result = disk_object.get_disks_wwn_mapping()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DiskFreeView(APIView):
    def get(self, request):
        disk_object = DiskTemp()
        result = disk_object.list_unpartitioned_disks()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DiskDeleteView(APIView):
    def delete(self, request):
        disk = request.data.get("disk_path")
        disk_object = DiskTemp()
        result = disk_object.wipe_disk_clean(disk)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DiskListView(APIView):
    def get(self, request):
        obj_dm = DiskManager()
        disks = obj_dm.get_disks_all(contain_os_disk=True)
        disk_dictionary = {}
        for disk in disks:
            disk_info = obj_dm.get_disk_info(disk)

            # جمع‌بندی اطلاعات در یک دیکشنری واحد
            disk_dictionary[disk] = {
                "info": disk_info,
            }

        return Response(disk_dictionary, status=status.HTTP_200_OK)

class DiskTestSuccessView(APIView):
    def get(self, request):
        from pylibs import StandardResponse
        return StandardResponse(data={"user": "ali"}, message="User fetched", save_to_db=True)




class DiskTestFailedView(APIView):
    def get(self, request):
        from pylibs import StandardErrorResponse
        return StandardErrorResponse(error_code="auth_failed", error_message="Invalid token", save_to_db=True )
