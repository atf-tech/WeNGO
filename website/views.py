from django.shortcuts import render

def index(request):
    return render(request, 'website/index.html')

def about(request):
    return render(request, 'website/about.html')

def service(request):
    return render(request, 'website/service.html')

def join_us(request):
    return render(request, 'website/join_us.html')

def contact(request):
    return render(request, 'website/contact.html')

def service_detail(request):
    return render(request, 'website/service_detail.html')

def termsConditions(request):
    return render(request, 'website/info/termsConditions.html')

def shippingPolicy(request):
    return render(request, 'website/info/shippingPolicy.html')

def privacyPolicy(request):
    return render(request, 'website/info/privacyPolicy.html')

def cancellationRefunds(request):
    return render(request, 'website/info/cancellationRefunds.html')
