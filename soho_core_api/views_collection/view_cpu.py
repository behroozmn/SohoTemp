from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from pylibs.cpu import CPU


@api_view(['GET'])
def cpu(myrequest):
    try:
        cpu_object = CPU()
        return Response(cpu_object.to_dict(), status.HTTP_200_OK)
    except RuntimeError as e:
        return Response({"error": str(e)}, status.HTTP_200_OK)

