from django.shortcuts import render, redirect ,get_object_or_404
from dashboard.models import *
from django.contrib import messages
from dashboard.views.auth import superuser_required


@superuser_required(login_url='/dashboard/login')
def visitor_chat(request):
    return render(request, 'dashboard/visitor_chat.html')
