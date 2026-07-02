from django.shortcuts import render, redirect ,get_object_or_404
from dashboard.models import *
from django.contrib import messages


def qr_donation(request):
    return render(request, 'dashboard/qr_donation.html')