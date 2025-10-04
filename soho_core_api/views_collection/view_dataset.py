from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pylibs.dataset import DatasetManager


class DatasetDetailView(APIView):
    def get(self, request):
        dataset_name = request.data.get("dataset_name")
        zfs_manager = DatasetManager()
        if dataset_name:
            result = zfs_manager.list_volume_detail(dataset_name)
        else:
            result = zfs_manager.list_volume_detail()
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)


class DatasetCreateView(APIView):
    def post(self, request):
        dataset_name = request.data.get("dataset_name", "None")
        volsize = request.data.get("volsize", "100G")
        zfs_manager = DatasetManager()
        result = zfs_manager.create(dataset_name, {"volsize": volsize})
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DatasetDeleteView(APIView):
    def delete(self, request):
        dataset_name = request.data.get("dataset_name", "None")
        zfs_manager = DatasetManager()
        result = zfs_manager.delete(dataset_name)
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
