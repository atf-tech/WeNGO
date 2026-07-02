from django.shortcuts import render,redirect
from website.models import *



def join_us(request):

   
    
    if request.method == "POST":
        dob = request.POST.get('dob') or None
        
        Volunteer.objects.create(
            name = request.POST.get("name"),
            email = request.POST.get("email"),
            mobile_no = request.POST.get("mobile_no"),
            gender = request.POST.get("gender"),
            dob = dob if dob else None,
            address = request.POST.get("address"),
            cv = request.FILES.get("cv")
        )
        return redirect("join_us")
    return render(request, 'website/join_us.html')
