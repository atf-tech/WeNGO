from django.shortcuts import render, redirect ,get_object_or_404
from dashboard.models import *
from django.contrib import messages


def Website_Donations(request):
    return render(request, 'dashboard/Website_Donations.html')