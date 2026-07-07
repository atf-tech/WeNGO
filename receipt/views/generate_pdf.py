from io import BytesIO

from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

from easypay.models import RMPayment
from receipt.models import Manual80GSubmission
from website.models import ServiceDonation

from .helper import get_template_name, get_pdf_filename


def generate_pdf(template_name, context):
    html_string = render_to_string(template_name, context)

    pdf_file = BytesIO()

    HTML(string=html_string).write_pdf(pdf_file)

    pdf_file.seek(0)

    return pdf_file


def download_pdf_response(pdf_file, filename):
    response = HttpResponse(
        pdf_file.read(),
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )

    return response


def build_donation_context(donation, donation_type):
    donor_pan = (
        getattr(donation, "donor_pan", None)
        or getattr(donation, "pan_number", None)
        or getattr(donation, "pan_no", None)
    )

    return {
        "donor_name": getattr(donation, "donor_name", ""),
        "donor_email": getattr(donation, "donor_email", ""),
        "donor_mobile": getattr(donation, "donor_mobile", ""),
        "donor_address": (
            getattr(donation, "donor_address", None)
            or getattr(donation, "address", "")
        ),
        "donor_pan": donor_pan,
        "amount": (
            getattr(donation, "donation_price", None)
            or getattr(donation, "donation_amount", None)
            or getattr(donation, "donor_amount", 0)
        ),
        "receipt_no": (
            getattr(donation, "receipt_no", None)
            or getattr(donation, "txnid", "")
        ),
        "date": (
            getattr(donation, "donation_date", None)
            or getattr(donation, "service_date", None)
            or getattr(donation, "submitted_at", None)
        ),
        "service_date": getattr(donation, "service_date", None),
        "payment_mode": (
            getattr(donation, "mode_of_donation", None)
            or getattr(donation, "easebuzz_payment_mode", None)
            or getattr(donation, "payment_mode", "")
        ),
        "donation_type": (donation_type or "Donation").title(),
    }


def generate_donation_pdf(donation, donation_type):
    donor_pan = (
        getattr(donation, "donor_pan", None)
        or getattr(donation, "pan_number", None)
        or getattr(donation, "pan_no", None)
    )

    template_name = get_template_name(donor_pan, donation_type)
    context = build_donation_context(donation, donation_type)

    return generate_pdf(template_name, context)


def get_donation_pdf_filename(donation, donation_type):
    donor_pan = (
        getattr(donation, "donor_pan", None)
        or getattr(donation, "pan_number", None)
        or getattr(donation, "pan_no", None)
    )

    return get_pdf_filename(
        getattr(donation, "donor_name", "donor"),
        donor_pan,
        donation_type,
    )


def download_donation_receipt(request):
    donation_type = (
        (request.GET.get("type") or request.GET.get("donation_type") or "")
        .strip()
        .lower()
    )
    receipt_reference = (
        request.GET.get("txnid")
        or request.GET.get("receipt_no")
        or request.GET.get("id")
    )

    if not donation_type or not receipt_reference:
        raise Http404("Receipt parameters missing")

    donation = None
    if donation_type == "service":
        donation = ServiceDonation.objects.filter(txnid=receipt_reference).first()
    elif donation_type == "rm":
        donation = RMPayment.objects.filter(txnid=receipt_reference).first()
    elif donation_type == "manual":
        donation = Manual80GSubmission.objects.filter(receipt_no=receipt_reference).first()
    else:
        raise Http404("Unsupported donation type")

    if not donation:
        raise Http404("Donation not found")

    pdf_file = generate_donation_pdf(donation, donation_type)
    filename = get_donation_pdf_filename(donation, donation_type)

    return download_pdf_response(pdf_file, filename)