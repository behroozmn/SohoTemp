from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from pylibs.zfs import ZFSManager
from rest_framework.response import Response


class ZFSStateView(APIView):
    permission_classes = [IsAdminUser]  # محدودسازی دسترسی؛ اختیاری

    def get(self, request):
        # فارسی: نمونه‌سازی از مدیر ZFS و گرفتن وضعیت کامل برای داشبورد.
        # EN: Instantiate manager and export full state for dashboards.
        mgr = ZFSManager(dry_run=False)
        return Response(mgr.export_full_state())


class CreateZvolView(APIView):
    def post(self, request):
        # JSON body: {"name":"tank/vms/vm01", "volsize":"50G", "volblocksize":"16K", "compression":"lz4"}
        body = request.data
        name = body.get("name")
        volsize = body.get("volsize")
        volblock = body.get("volblocksize", "16K")
        comp = body.get("compression", "lz4")

        if not name or not volsize:
            return Response({"ok": False, "error": {"message": "name and volsize are required"}}, status=status.HTTP_400_BAD_REQUEST)

        mgr = ZFSManager() # Create volume dataset then apply additional properties.
        req1 = mgr.create_dataset(name, properties={"volsize": volsize, "volblocksize": volblock}, dataset_type="volume")
        if not req1["ok"]:
            return Response(req1, status=status.HTTP_400_BAD_REQUEST)
        req2 = mgr.set_props(name, {"compression": comp, "sync": "standard"})
        return Response({"create": req1, "tune": req2})
