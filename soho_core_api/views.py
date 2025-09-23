from django.http import JsonResponse


def index(myrequest):
    general = ["cpu", "memory", "net"]  # هنوز دیتای درست وارد نکردم
    return JsonResponse({'General': general})  # هنوز دیتای درست وارد نکردم









