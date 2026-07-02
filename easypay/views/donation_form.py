from django.conf import settings
from django.shortcuts import render, get_object_or_404

from dashboard.models import RM

def rm_donation_form(request, rm_code):
    print("========== RM DONATION VIEW HIT ==========")
    print("RM Code:", rm_code)

    rm = get_object_or_404(RM, rm_code=rm_code)

    easebuzz = {
        "merchant_key": settings.EASEBUZZ_MERCHANT_KEY,
        "env": settings.EASEBUZZ_ENV,
    }

    return render(
        request,
        "easypay/rm_donation_form.html",
        {
            "rm": rm,
            "easebuzz": easebuzz,
        },
    )
