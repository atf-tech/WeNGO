from django.conf import settings
from django.core.mail import EmailMessage

from .helper import get_amount, get_date_label, DONATION_TYPE_LABELS
from .generate_pdf import generate_donation_pdf, get_donation_pdf_filename


def send_donation_success_email(donation, request, donation_type):
    amount = get_amount(donation)
    date_label = get_date_label(donation_type)
    donation_type_label = DONATION_TYPE_LABELS.get(donation_type, "Donation")

    date_value = getattr(donation, 'donation_date', None) or getattr(donation, 'service_date', None) or 'N/A'
    if hasattr(date_value, 'strftime'):
        date_value = date_value.strftime('%d-%m-%Y')

    email_body = f"""
Dear {donation.donor_name},

Thank you for your generous {donation_type_label}. We deeply appreciate your support.

Please find below your donation receipt details:

Donor Name      : {donation.donor_name}
Mobile Number   : {donation.donor_mobile}
Email ID        : {donation.donor_email}
{date_label}    : {date_value}
Amount          : ₹{amount}

Please find the attached receipt for your reference.

Best regards,
Women Empowerment NGO
"""

    filename = f"{donation.donor_name.replace(' ', '_')}.pdf"

    email = EmailMessage(
        subject=f"Your {donation_type_label} Receipt – Women Empowerment NGO",
        body=email_body,
        from_email=f"Women Empowerment NGO <{settings.DEFAULT_FROM_EMAIL}>",
        to=[donation.donor_email],
        bcc=["worldwebtechmail@gmail.com"],
    )
    try:
        pdf_file = generate_donation_pdf(
            donation,
            donation_type
        )
    
        email.attach(
            get_donation_pdf_filename(
                donation,
                donation_type
            ),
            pdf_file.read(),
            "application/pdf"
        )
    
    except Exception as e:
        print("PDF ATTACH ERROR:", e)
    
    email.send()