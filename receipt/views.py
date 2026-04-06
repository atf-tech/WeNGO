from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import datetime
from io import BytesIO
from weasyprint import HTML
from .models import Manual80GSubmission


def parse_form_data(request):
    donor_name = request.POST.get("manual-donor-name", "").strip()
    donor_email = request.POST.get("manual-donor-Email", "").strip()
    donor_mobile = request.POST.get("manual-donor-mob-no", "").strip()
    service_date_str = request.POST.get("manual-service-date", "")
    donation_date_str = request.POST.get("manual-donation-date", "")
    donor_pan = request.POST.get("manual-donor-pan", "").strip()
    donation_price = request.POST.get("manual-donation-price", "").strip()
    donor_address = request.POST.get("manual-donor-address", "").strip()
    receipt_no = request.POST.get("manual-receipt-no", "").strip()
    mode_of_donation = request.POST.get("manual-mod", "").strip()

    service_date = (
        datetime.strptime(service_date_str, "%Y-%m-%d").date()
        if service_date_str
        else None
    )
    donation_date = (
        datetime.strptime(donation_date_str, "%Y-%m-%d").date()
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


def get_template_name(donor_pan):
    if donor_pan and donor_pan.strip():
        return "receipt/manual_80g.html"
    return "receipt/manual_donation_receipt.html"


def get_pdf_filename(donor_name, donor_pan):
    donor_name_clean = donor_name.replace(" ", "_")
    if donor_pan and donor_pan.strip():
        return f"{donor_name_clean}_80g.pdf"
    return f"{donor_name_clean}.pdf"


def generate_pdf(template_name, context):
    html_string = render_to_string(template_name, context)
    pdf_file = BytesIO()
    HTML(string=html_string).write_pdf(pdf_file)
    pdf_file.seek(0)
    return pdf_file


@csrf_exempt
def manual_80g_mail(request):
    message = ""

    if request.method == "POST":
        try:
            data = parse_form_data(request)

            manual, created = Manual80GSubmission.objects.get_or_create(
                receipt_no=data["receipt_no"],
                defaults={
                    "donor_name": data["donor_name"],
                    "donor_email": data["donor_email"],
                    "donor_mobile": data["donor_mobile"],
                    "service_date": data["service_date"],
                    "donation_date": data["donation_date"],
                    "donor_pan": data["donor_pan"],
                    "donation_price": data["donation_price"],
                    "donor_address": data["donor_address"],
                    "mode_of_donation": data["mode_of_donation"],
                },
            )

            template_name = get_template_name(data["donor_pan"])
            pdf_file = generate_pdf(template_name, {"manual": manual})
            pdf_filename = get_pdf_filename(data["donor_name"], data["donor_pan"])

            email_body = f"""
Dear {manual.donor_name},

Thank you for your generous donation. We deeply appreciate your support.

Please find below your donation receipt details:

Donor Name      : {manual.donor_name}
Mobile Number   : {manual.donor_mobile}
Email ID        : {manual.donor_email}
Date            : {manual.donation_date.strftime('%d-%m-%Y') if manual.donation_date else 'N/A'}

Please find the attached receipt for your reference.

Best regards,
Women Empowerment NGO
"""

            email = EmailMessage(
                subject="Your Donation Receipt – Women Empowerment NGO",
                body=email_body,
                from_email=f"Women Empowerment NGO <{settings.DEFAULT_FROM_EMAIL}>",
                to=[data["donor_email"]],
                bcc=["worldwebtechmail@gmail.com"],
            )
            email.attach(pdf_filename, pdf_file.read(), "application/pdf")
            email.send()

            message = "Form submitted successfully. Receipt sent to your email."

        except Exception as e:
            print("Submission Error:", e)
            message = "There was an error submitting the form or sending the email. Please try again."

    return render(request, "receipt/eightyg_manual.html", {"message": message})


@never_cache
@csrf_exempt
def manual_80g_download(request):

    if request.method == "POST":
        try:
            data = parse_form_data(request)

            # Save to DB so we have a proper model object for the template
            manual, created = Manual80GSubmission.objects.get_or_create(
                receipt_no=data["receipt_no"],
                defaults={
                    "donor_name": data["donor_name"],
                    "donor_email": data["donor_email"],
                    "donor_mobile": data["donor_mobile"],
                    "service_date": data["service_date"],
                    "donation_date": data["donation_date"],
                    "donor_pan": data["donor_pan"],
                    "donation_price": data["donation_price"],
                    "donor_address": data["donor_address"],
                    "mode_of_donation": data["mode_of_donation"],
                },
            )

            template_name = get_template_name(data["donor_pan"])
            pdf_file = generate_pdf(template_name, {"manual": manual})
            pdf_filename = get_pdf_filename(data["donor_name"], data["donor_pan"])

            response = HttpResponse(pdf_file.read(), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{pdf_filename}"'
            return response

        except Exception as e:
            print("Download Error:", e)
            return HttpResponse("Error generating receipt. Please try again.")

    return HttpResponse("Invalid request method.")
