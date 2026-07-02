from io import BytesIO

from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

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


def generate_donation_pdf(donation, donation_type):

    donor_pan = (
        getattr(donation, "donor_pan", None)
        or getattr(donation, "pan_number", None)
        or getattr(donation, "pan_no", None)
    )

    template_name = get_template_name(
        donor_pan,
        donation_type
    )

    context = {
        "donor_name": donation.donor_name,
        "donor_email": donation.donor_email,
        "donor_mobile": donation.donor_mobile,

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

        "service_date": getattr(
            donation,
            "service_date",
            None
        ),

        "payment_mode": (
            getattr(donation, "mode_of_donation", None)
            or getattr(donation, "easebuzz_payment_mode", None)
            or getattr(donation, "payment_mode", "")
        ),

        "donation_type": donation_type.title(),
    }

    return generate_pdf(
        template_name,
        context
    )


def get_donation_pdf_filename(donation, donation_type):
    donor_pan = (
        getattr(donation, "donor_pan", None)
        or getattr(donation, "pan_number", None)
        or getattr(donation, "pan_no", None)
    )
    
    return get_pdf_filename(
        donation.donor_name,
        donor_pan,
        donation_type
    )