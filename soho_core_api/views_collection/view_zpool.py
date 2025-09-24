
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.pool import PoolManager

class zPoolListView(APIView):
    """List all pools (GET) or create a new pool (POST - not implemented)."""

    def get(self, request):
        manager = PoolManager()
        result = manager.list_pools()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        name = request.data.get("name", "None")
        return Response({
            "ok": False,
            "error": {
                "code": "not_implemented",
                "message": "Pool creation is not implemented in PoolManager yet."
            },
            "data": None,
            "meta": {}
        }, status=status.HTTP_501_NOT_IMPLEMENTED)

