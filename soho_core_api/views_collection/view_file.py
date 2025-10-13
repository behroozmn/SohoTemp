from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.file import FileManager  # مسیر واردات را با پروژه‌تان تطبیق دهید


class SetPermissionsView(APIView):
    def post(self, request):
        path = request.data.get("path")
        mode = request.data.get("mode", "0755")
        owner = request.data.get("owner")
        group = request.data.get("group")
        recursive = request.data.get("recursive", True)

        if not all([path, owner, group]):
            return Response(
                {"ok": False, "error": {"code": "missing_fields", "message": "Missing required fields: path, owner, group"}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        fm = FileManager()
        result = fm.set_permissions(path, mode, owner, group, recursive)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateDirectoryView(APIView):
    def post(self, request):
        path = request.data.get("path")
        mode = request.data.get("mode", "0755")
        owner = request.data.get("owner")
        group = request.data.get("group")

        if not all([path, owner, group]):
            return Response(
                {"ok": False, "error": {"code": "missing_fields", "message": "Missing required fields: path, owner, group"}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        fm = FileManager()
        result = fm.create_directory(path, mode, owner, group)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetFileInfoView(APIView):
    def get(self, request):
        path = request.data.get("path")
        if not path:
            return Response(
                {"ok": False, "error": {"code": "missing_param", "message": "Missing 'path' query parameter"}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        fm = FileManager()
        result = fm.get_file_info(path)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
