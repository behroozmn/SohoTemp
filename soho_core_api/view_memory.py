from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from pylibs.memory import Memory


@api_view(['GET'])
def memory(myrequest):
    try:
        mem = Memory()
        return Response(mem.to_dict(), status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status.HTTP_200_OK)