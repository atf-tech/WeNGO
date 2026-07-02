from django.shortcuts import render,redirect
from website.models import *



def contact(request):

    if request.method == "POST":
        Contact.objects.create(
            name = request.POST.get("name"),
            email = request.POST.get("email"),
            subject = request.POST.get("subject"),
            message = request.POST.get("message")
        )
        return redirect("contact")
    return render(request, 'website/contact.html')