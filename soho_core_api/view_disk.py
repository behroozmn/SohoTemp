from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from pylibs.disk import Disk


@api_view(['GET'])
def disk(myrequest):
    try:
        disk_object = Disk()
        return Response(disk_object.to_dict(), status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status.HTTP_200_OK)

