from django.shortcuts import render, redirect
from django.contrib import messages
from dashboard.models import *
from dashboard.views.auth import superuser_required


@superuser_required(login_url='/dashboard/login')
def add_items(request):

    if request.method == "POST":

        # ========================= HOME ========================= #

        home_id = request.POST.get("home_id")

        if home_id is not None:

            action = request.POST.get("action")

            if action == "delete":
                Home.objects.filter(id=home_id).delete()
                messages.success(request, "Home Deleted Successfully")
                return redirect("add_items")

            if home_id:
                try:
                    home = Home.objects.get(id=home_id)

                    home.name = request.POST.get("name")
                    home.description = request.POST.get("description")
                    home.members = request.POST.get("member")

                    if request.FILES.get("image"):
                        home.home_image = request.FILES.get("image")

                    home.save()

                    messages.success(request, "Home Updated Successfully")

                except Home.DoesNotExist:
                    messages.error(request, "Home not found.")

                return redirect("add_items")

            Home.objects.create(
                name=request.POST.get("name"),
                description=request.POST.get("description"),
                members=request.POST.get("member"),
                home_image=request.FILES.get("image")
            )

            messages.success(request, "Home Added Successfully")
            return redirect("add_items")



        # ========================= SERVICE ========================= #



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

    homes = Home.objects.all().order_by("-id")
    services = Services.objects.all().order_by("display_order")

    return render(
        request,
        "dashboard/add_items.html",
        {
            "homes": homes,
            "services": services,
        },
    )