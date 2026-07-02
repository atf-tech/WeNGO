from django.shortcuts import render,redirect
from dashboard.models import Services
from django.shortcuts import render, get_object_or_404


def index(request):
    services = Services.objects.all().order_by("display_order")
    return render(request, 'website/index.html',{"services": services})