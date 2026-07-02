from django.shortcuts import render, redirect ,get_object_or_404
from dashboard.models import *
from django.contrib import messages



def add_items(request):

    if request.method == "POST":

        action = request.POST.get("action")
        service_id = request.POST.get("service_id")

       
        if action == "delete":
            Services.objects.filter(id=service_id).delete()
            messages.success(request, "Service Deleted Successfully")
            return redirect("add_items")

        
        if service_id:
            service = Services.objects.get(id=service_id)

            service.service_name = request.POST.get("service_name")
            service.description = request.POST.get("description")
            service.amount = request.POST.get("amount")
            service.target_amount = request.POST.get("target_amount")
            service.min_quantity = request.POST.get("min_quantity")
            service.display_order = request.POST.get("display_order")
            service.is_food_service = bool(request.POST.get("is_food_service"))

            if request.FILES.get("image"):
                service.image = request.FILES.get("image")

            service.save()

            messages.success(request, "Service Updated Successfully")
            return redirect("add_items")

        
        Services.objects.create(
            service_name=request.POST.get("service_name"),
            description=request.POST.get("description"),
            amount=request.POST.get("amount"),
            target_amount=request.POST.get("target_amount"),
            min_quantity=request.POST.get("min_quantity"),
            display_order=request.POST.get("display_order"),
            image=request.FILES.get("image"),
            is_food_service=bool(request.POST.get("is_food_service"))
        )

        messages.success(request, "Service Added Successfully")
        return redirect("add_items")

    services = Services.objects.all().order_by("display_order")

    return render(
        request,
        "dashboard/add_items.html",
        {"services": services}
    )