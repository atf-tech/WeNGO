from decimal import Decimal

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache

from dashboard.models import RM
from easypay.models import RMGPayPayment

from .auth import rm_login_required

@never_cache
@rm_login_required
def rm_gpay_payments(request, rm_code):
    rm = get_object_or_404(RM, rm_code=rm_code)

    if request.method == "POST":
        action = request.POST.get("action")

        # ---------------- CREATE ----------------
        if action == "create":
            donor_name = request.POST.get("donor_name") or None
            donor_email = request.POST.get("donor_email") or None
            donor_mobile = request.POST.get("donor_mobile") or None
            donor_address = request.POST.get("donor_address") or None
            payment_date = request.POST.get("payment_date") or None
            package_type = request.POST.get("package_type") or None
            gpay_reference_id = request.POST.get("gpay_reference_id") or None
            donor_pan = (request.POST.get("donor_pan") or "").strip().upper() or None
            payment_screenshot = request.FILES.get("payment_screenshot")

            amount_raw = request.POST.get("amount")

            if payment_date and amount_raw:
                amount = Decimal(amount_raw)

                RMGPayPayment.objects.create(
                    rm=rm,
                    rm_code=rm.rm_code,
                    rm_name=rm.rm_name,
                    rm_email=rm.rm_email,
                    donor_name=donor_name,
                    donor_email=donor_email,
                    donor_mobile=donor_mobile,
                    donor_address=donor_address,
                    payment_date=payment_date,
                    donor_pan=donor_pan,
                    amount=amount,
                    gpay_reference_id=gpay_reference_id,
                    package_type=package_type,
                    payment_screenshot=payment_screenshot,
                )

        # ---------------- UPDATE ----------------
        elif action == "update":
            payment = get_object_or_404(
                RMGPayPayment,
                id=request.POST.get("payment_id"),
                rm=rm,
            )
        
            payment.donor_name = request.POST.get("donor_name") or None
            payment.donor_email = request.POST.get("donor_email") or None
            payment.donor_mobile = request.POST.get("donor_mobile") or None
            payment.donor_address = request.POST.get("donor_address") or None
            payment.payment_date = request.POST.get("payment_date") or None
            payment.package_type = request.POST.get("package_type") or None
            payment.gpay_reference_id = request.POST.get("gpay_reference_id") or None
            payment.donor_pan = (
                request.POST.get("donor_pan") or ""
            ).strip().upper() or None
        
            amount_raw = request.POST.get("amount")
            if amount_raw:
                payment.amount = Decimal(amount_raw)
        
            if request.FILES.get("payment_screenshot"):
                payment.payment_screenshot = request.FILES["payment_screenshot"]
        
            payment.save()

        # ---------------- DELETE ----------------
        elif action == "delete":
            payment = get_object_or_404(
                RMGPayPayment,
                id=request.POST.get("payment_id"),
                rm=rm,
            )
            payment.delete()

        return redirect("rm_gpay_payments", rm_code=rm.rm_code)

    gpay_payments = RMGPayPayment.objects.filter(rm=rm).order_by("-payment_date")

    return render(
        request,
        "add_gpay_payments.html",
        {
            "rm": rm,
            "gpay_payments": gpay_payments,
        },
    )