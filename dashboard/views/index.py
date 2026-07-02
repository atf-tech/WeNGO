from django.shortcuts import render, redirect ,get_object_or_404
from dashboard.models import *
from django.contrib import messages


def index(request):
    return render(request, 'dashboard/index.html')