from datetime import datetime

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache

from receipt.models import Manual80GSubmission

from .helper import get_pdf_filename
from .generate_pdf import (
    generate_donation_pdf,
    download_pdf_response,
)
from .success_mail import send_donation_success_email
from .failed_mail import send_donation_failed_email


def parse_form_data(request):

    donor_name = request.POST.get(
        "manual-donor-name",
        ""
    ).strip()

    donor_email = request.POST.get(
        "manual-donor-Email",
        ""
    ).strip()

    donor_mobile = request.POST.get(
        "manual-donor-mob-no",
        ""
    ).strip()

    service_date_str = request.POST.get(
        "manual-service-date",
        ""
    )

    donation_date_str = request.POST.get(
        "manual-donation-date",
        ""
    )

    donor_pan = request.POST.get(
        "manual-donor-pan",
        ""
    ).strip()

    donation_price = request.POST.get(
        "manual-donation-price",
        ""
    ).strip()

    donor_address = request.POST.get(
        "manual-donor-address",
        ""
    ).strip()

    receipt_no = request.POST.get(
        "manual-receipt-no",
        ""
    ).strip()

    mode_of_donation = request.POST.get(
        "manual-mod",
        ""
    ).strip()

    service_date = (
        datetime.strptime(
            service_date_str,
            "%Y-%m-%d"
        ).date()
        if service_date_str
        else None
    )

    donation_date = (
        datetime.strptime(
            donation_date_str,
            "%Y-%m-%d"
        ).date()
        if donation_date_str
        else None
    )

    return {
        "donor_name": donor_name,
        "donor_email": donor_email,
        "donor_mobile": donor_mobile,
        "service_date": service_date,
        "donation_date": donation_date,
        "donor_pan": donor_pan,
        "donation_price": donation_price,
        "donor_address": donor_address,
        "receipt_no": receipt_no,
        "mode_of_donation": mode_of_donation,
    }


def save_manual_submission(data):

    manual, created = (
        Manual80GSubmission.objects.get_or_create(
            receipt_no=data["receipt_no"],
            defaults=data,
        )
    )

    return manual


@csrf_exempt
def manual_80g_mail(request):

    message = ""
    manual = None

    if request.method == "POST":

        try:

            data = parse_form_data(request)

            manual = save_manual_submission(data)

            pdf_file = generate_donation_pdf(
                manual,
                "manual",
            )

            pdf_filename = get_pdf_filename(
                data["donor_name"],
                data["donor_pan"],
            )

            manual._pdf_file = pdf_file
            send_donation_success_email(
                manual,
                request,
                "manual"
            )

            message = (
                "Form submitted successfully."
            )

        except Exception as e:

            print(
                "Submission Error:",
                e
            )

            if manual:
                send_donation_failed_email(
                    manual,
                    "manual",
                    request
                )

            message = (
                "There was an error."
            )

    return render(
        request,
        "receipt/eightyg_manual.html",
        {"message": message},
    )


@never_cache
@csrf_exempt
def manual_80g_download(request):

    if request.method == "POST":

        try:

            data = parse_form_data(request)

            manual = save_manual_submission(data)

            pdf_file = generate_donation_pdf(
                manual,
                "manual",
            )

            pdf_filename = get_pdf_filename(
                data["donor_name"],
                data["donor_pan"],
            )

            return download_pdf_response(
                pdf_file,
                pdf_filename,
            )

        except Exception as e:

            print(
                "Download Error:",
                e
            )

    from django.http import HttpResponse

    return HttpResponse(
        "Invalid request method."
    )