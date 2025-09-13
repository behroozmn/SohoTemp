from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from pylibs.network import Network
from pylibs.memory import Memory
from pylibs.cpu import CPU
from pylibs.disk import Disk


def index(myrequest):
    general = ["cpu", "memory", "net"]  # هنوز دیتای درست وارد نکردم
    return JsonResponse({'General': general})  # هنوز دیتای درست وارد نکردم


@api_view(['GET'])
def cpu(myrequest):
    try:
        cpu_object = CPU()
        return Response(cpu_object.to_dict(), status.HTTP_200_OK)
    except RuntimeError as e:
        return Response({"error": str(e)}, status.HTTP_200_OK)


@api_view(['GET'])
def network(request):
    try:
        net = Network()
        return Response(net.to_dict(), status.HTTP_200_OK)
    except RuntimeError as e:
        return Response({"error": str(e)}, status.HTTP_200_OK)


@api_view(['GET'])
def memory(myrequest):
    try:
        mem = Memory()
        return Response(mem.to_dict(), status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status.HTTP_200_OK)


@api_view(['GET'])
def disk(myrequest):
    try:
        disk_object = Disk()
        return Response(disk_object.to_dict(), status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status.HTTP_200_OK)
