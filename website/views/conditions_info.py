from django.shortcuts import render,redirect
from dashboard.models import Services
from django.shortcuts import render, get_object_or_404




def termsConditions(request):
    return render(request, 'website/info/termsConditions.html')

def shippingPolicy(request):
    return render(request, 'website/info/shippingPolicy.html')

def privacyPolicy(request):
    return render(request, 'website/info/privacyPolicy.html')

def cancellationRefunds(request):
    return render(request, 'website/info/cancellationRefunds.html')