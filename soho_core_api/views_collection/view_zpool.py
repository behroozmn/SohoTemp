# zfs_api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from pylibs.zpool import PoolManager


class ZPoolListView(APIView):
    """List all pools (GET) or create a new pool (POST - not implemented)."""

    def get(self, request):
        manager = PoolManager()
        result = manager.list_pools()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        return Response({
            "ok": False,
            "error": {
                "code": "not_implemented",
                "message": "Pool creation is not implemented in ZPoolManager yet."
            },
            "data": None,
            "meta": {}
        }, status=status.HTTP_501_NOT_IMPLEMENTED)


@method_decorator(csrf_exempt, name='dispatch')
class ZPoolDetailView(APIView):
    """Get, update, or delete a specific pool."""

    def get_pool_or_404(self, pool_name):
        manager = PoolManager()
        info = manager.pool_info(pool_name)
        if not info["ok"]:
            raise Http404(f"Pool '{pool_name}' not found.")
        return pool_name

    def get(self, request, pool_name):
        manager = PoolManager()
        result = manager.pool_info(pool_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pool_name):
        prop = request.data.get("prop")
        value = request.data.get("value")
        if not prop or value is None:
            return Response({
                "ok": False,
                "error": {"code": "invalid_input", "message": "'prop' and 'value' are required."},
                "data": None,
                "meta": {}
            }, status=status.HTTP_400_BAD_REQUEST)

        manager = PoolManager()
        result = manager.edit_pool_prop(pool_name, prop, str(value))
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pool_name):
        manager = PoolManager()
        result = manager.delete_pool(pool_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class ZPoolDatasetsView(APIView):
    """List datasets (filesystems/volumes) in a pool."""

    def get(self, request, pool_name):
        manager = PoolManager()
        result = manager.list_datasets_info(pool_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)


@method_decorator(csrf_exempt, name='dispatch')
class ZPoolDevicesView(APIView):
    """List detailed device info (vdevs) in a pool."""

    def get(self, request, pool_name):
        manager = PoolManager()
        result = manager.list_pool_devices(pool_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)


@method_decorator(csrf_exempt, name='dispatch')
class ZPoolDeviceNamesView(APIView):
    """List only device paths in a pool."""

    def get(self, request, pool_name):
        manager = PoolManager()
        result = manager.list_pool_device_names(pool_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)


@method_decorator(csrf_exempt, name='dispatch')
class ZPoolFeaturesView(APIView):
    """List ZFS feature states (feature@*) for a pool."""

    def get(self, request, pool_name):
        manager = PoolManager()
        result = manager.pool_features(pool_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)


@method_decorator(csrf_exempt, name='dispatch')
class ZPoolCapacityView(APIView):
    """Get capacity usage (size, free, allocated) of a pool."""

    def get(self, request, pool_name):
        manager = PoolManager()
        result = manager.pool_capacity(pool_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)


# =============== [اختیاری: برای آینده — ایجاد pool] ===============
@method_decorator(csrf_exempt, name='dispatch')
class ZPoolCreateView(APIView):
    """
    Create a new ZFS pool.
    NOT IMPLEMENTED in current ZPoolManager, but ready for extension.
    Expected body:
    {
        "name": "newpool",
        "devices": ["/dev/sdb", "/dev/sdc"],
        "properties": {"autotrim": "on", "ashift": "12"}
    }
    """

    def post(self, request):
        return Response({
            "ok": False,
            "error": {
                "code": "not_implemented",
                "message": "Pool creation is not implemented in ZPoolManager yet."
            },
            "data": None,
            "meta": {}
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
