from django.shortcuts import render

def home(request):
    return render(request, 'dashboard/home.html')

def index(request):
    return render(request, 'dashboard/index.html')

def visitor_chat(request):
    return render(request, 'dashboard/visitor_chat.html')

def Website_Donations(request):
    return render(request, 'dashboard/Website_Donations.html')

def RM_S(request):
    return render(request, 'dashboard/RM_S.html')

def RM_Portal(request):
    return render(request, 'dashboard/RM_Portal.html')

def qr_donation(request):
    return render(request, 'dashboard/qr_donation.html')

def admin_search_page(request):
    return render(request, 'dashboard/admin_search_page.html')
