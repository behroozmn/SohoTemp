from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from pylibs.disk import Disk


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


    #  = get_disk_wwn_mapping()
    #  = get_all_disks()
    #
    # print(f"{'Device':<12} {'WWN'}")
    # print("-" * 60)
    #
