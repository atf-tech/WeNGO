from django.shortcuts import render,redirect
from dashboard.models import *
from django.shortcuts import render, get_object_or_404


def index(request):
    homes = Home.objects.all().order_by("id")
    services = Services.objects.all().order_by("display_order")

    context = {
        "homes": homes,
        "services": services,
    }

    return render(request, "website/index.html", context)