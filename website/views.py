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




def payment_success(request):
    return render(request, 'website/success.html')

def payment_failed(request):
    return render(request, 'website/failed.html')




def wheel_chair(request):
    return render(request, 'website/causes/wheel_chair.html')

def veg_briyani(request):
    return render(request, 'website/causes/veg_briyani.html')

def school_bag(request):
    return render(request, 'website/causes/school_bag.html')

def grocery_kit(request):
    return render(request, 'website/causes/grocery_kit.html')

def dresses(request):
    return render(request, 'website/causes/dresses.html')

def birds_feeding(request):
    return render(request, 'website/causes/birds_feeding.html')