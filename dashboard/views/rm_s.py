from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from dashboard.models import RM
from dashboard.views.auth import superuser_required


@superuser_required(login_url='/dashboard/login')
def RM_S(request):

    if request.method == "POST":

        action = request.POST.get("action")
        rm_id = request.POST.get("rm_id")

        password = request.POST.get("rm_password")
        confirm_password = request.POST.get("confirm_password")

        # PASSWORD CHECK
        if not rm_id:
            if password and password != confirm_password:
                messages.error(request, "Password didn't match")
                return redirect("RM_S")


        if action == "delete" and rm_id:
            RM.objects.filter(id=rm_id).delete()
            messages.success(request, "RM Deleted Successfully")
            return redirect("RM_S")

       
        # UPDATE RM
       
        if rm_id:
            rm = get_object_or_404(RM, id=rm_id)

            name = request.POST.get("rm_name")

            # duplicate check (exclude current)
            if RM.objects.exclude(id=rm_id).filter(rm_name__iexact=name).exists():
                messages.warning(request, "RM Name already exists")
                return redirect("RM_S")

            rm.rm_name = name
            rm.rm_mob_no = request.POST.get("rm_mob_no")
            rm.rm_email = request.POST.get("rm_email")
            rm.rm_branch = request.POST.get("rm_branch")
            rm.rm_gender = request.POST.get("rm_gender")
            rm.tl_name = request.POST.get("tl_name")
            rm.target_amount = request.POST.get("target_amount") or 0

            # safe boolean
            rm.is_active = True if request.POST.get("rm_active") == "on" else False
            rm.active_whatsapp = True if request.POST.get("active_whatsapp") == "on" else False
            rm.active_visitor_chat = True if request.POST.get("active_visitor_chat") == "on" else False

            # password update only if given
            if password:
                rm.rm_password = make_password(password)

            # QR image update
            if request.FILES.get("qr_image"):
                rm.qr_image = request.FILES.get("qr_image")

            rm.save()
            messages.success(request, "RM Updated Successfully")
            return redirect("RM_S")

       
        # CREATE RM
       
        name = request.POST.get("rm_name")

        if RM.objects.filter(rm_name__iexact=name).exists():
            messages.warning(request, "RM Name already exists")
            return redirect("RM_S")

        RM.objects.create(
            rm_name=name,
            rm_mob_no=request.POST.get("rm_mob_no"),
            rm_email=request.POST.get("rm_email"),
            rm_password=make_password(password or ""),
            rm_branch=request.POST.get("rm_branch"),
            rm_gender=request.POST.get("rm_gender"),
            tl_name=request.POST.get("tl_name"),
            target_amount=request.POST.get("target_amount") or 0,
            qr_image=request.FILES.get("qr_image"),
            is_active=request.POST.get("rm_active") == "on",
            active_whatsapp=request.POST.get("active_whatsapp") == "on",
            active_visitor_chat=request.POST.get("active_visitor_chat") == "on",
        )

        messages.success(request, "RM Added Successfully")
        return redirect("RM_S")

    
    selected_rm = request.GET.get("rm_name", "").strip()

    rm_list = RM.objects.all().order_by("-id")

    if selected_rm and selected_rm.lower() != "all":
        rm_s = RM.objects.filter(rm_name__iexact=selected_rm).order_by("-id")
    else:
        rm_s = rm_list

    # RM LINK GENERATION
    for rm in rm_s:
        rm.rm_link = request.build_absolute_uri(
            reverse("rm_donation_form", args=[rm.rm_code])
        )

    return render(request, "dashboard/RM_S.html", {
        "rm_s": rm_s,
        "rm_list": rm_list,
    })