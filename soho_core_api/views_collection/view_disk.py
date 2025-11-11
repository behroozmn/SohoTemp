from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from pylibs.disk import DiskManager


class DiskListView(APIView):
    def get(self, request):
        from pylibs import (StandardResponse,StandardErrorResponse)
        from pylibs.disk import DiskManager
        obj_disk = DiskManager()
        return StandardResponse(data=obj_disk.get_disks_info_all(), message="User fetched", save_to_db=True)

class DiskTestSuccessView(APIView):
    def get(self, request):
        from pylibs import StandardResponse
        return StandardResponse(data={"user": "ali"}, message="User fetched", save_to_db=True)




class DiskTestFailedView(APIView):
    def get(self, request):
        from pylibs import StandardErrorResponse
        return StandardErrorResponse(error_code="auth_failed", error_message="Invalid token", save_to_db=True )
