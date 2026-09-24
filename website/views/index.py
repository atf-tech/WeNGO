from django.shortcuts import render,redirect
from dashboard.models import *
from django.shortcuts import render, get_object_or_404


def index(request):
    homes = Home.objects.all().order_by("id")

    context = {
        "homes": homes,
    }

    return render(request, "website/index.html", context)
