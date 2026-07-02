from django.shortcuts import render, redirect ,get_object_or_404
from dashboard.models import *
from django.contrib import messages





def RM_Portal(request):
    return render(request, 'dashboard/RM_Portal.html')
