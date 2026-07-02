from django.shortcuts import render, redirect ,get_object_or_404
from dashboard.models import *
from django.contrib import messages


def admin_search_page(request):
    return render(request, 'dashboard/admin_search_page.html')