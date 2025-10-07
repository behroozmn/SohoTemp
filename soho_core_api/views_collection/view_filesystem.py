from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.filesystem import FilesystemManager


class FilesystemDetailView(APIView):
    def get(self, request):
        zfs_manager = FilesystemManager()
        result = zfs_manager.list_filesystem_detail()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)


class FilesystemCreateView(APIView):
    def post(self, request):
        filesystem_name = request.data.get("filesystem_name", "None")
        qouta = request.data.get("quota")
        reservation = request.data.get("reservation")
        properties = {"quota": qouta, "reservation": reservation}

        zfs_manager = FilesystemManager()
        result = zfs_manager.create(filesystem_name,properties=properties)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FilesystemDeleteView(APIView):
    def delete(self, request):
        filesystem_name = request.data.get("filesystem_name", "None")
        zfs_manager = FilesystemManager()
        result = zfs_manager.delete(filesystem_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
