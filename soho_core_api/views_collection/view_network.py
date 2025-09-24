from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from pylibs.network import Network


@api_view(['GET'])
def network(request):
    try:
        net = Network()
        return Response(net.to_dict(), status.HTTP_200_OK)
    except RuntimeError as e:
        return Response({"error": str(e)}, status.HTTP_200_OK)
