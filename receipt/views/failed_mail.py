from django.conf import settings
from django.core.mail import EmailMessage

from .helper import DONATION_TYPE_LABELS


def send_donation_failed_email(donation, donation_type, request):
    donation_type_label = DONATION_TYPE_LABELS.get(donation_type, "Donation")

    retry_url = ""
    if donation_type == "manual":
        retry_url = ""
    elif donation_type == "service":
        retry_url = request.build_absolute_uri(f"/service/retry/{donation.id}/")
    # elif donation_type == "home":
    #     retry_url = request.build_absolute_uri(f"/home/retry/{donation.id}/")
    # elif donation_type == "student":
    #     retry_url = request.build_absolute_uri(f"/student/retry/{donation.id}/")
    # elif donation_type == "festival":
    #     retry_url = request.build_absolute_uri(f"/festival/retry/{donation.id}/")
    # elif donation_type == "birthday":
    #     retry_url = request.build_absolute_uri(f"/birthday/retry/{donation.id}/")
    elif donation_type == "rm":
        retry_url = request.build_absolute_uri(f"/rm/retry/{donation.id}/")

    if retry_url:
        email_body = f"""
Dear {donation.donor_name},

We regret to inform you that there was an error processing your {donation_type_label} receipt.

Please click the link below to retry your donation:
{retry_url}

Best regards,
Women Empowerment NGO
"""
    else:
        email_body = f"""
Dear {donation.donor_name},

We regret to inform you that there was an error processing your {donation_type_label} receipt.

Please contact us for assistance.

Best regards,
Women Empowerment NGO
"""

    email = EmailMessage(
        subject=f"Donation Receipt Processing Failed – Women Empowerment NGO",
        body=email_body,
        from_email=f"Women Empowerment NGO <{settings.DEFAULT_FROM_EMAIL}>",
        to=[donation.donor_email],
        bcc=["worldwebtechmail@gmail.com"],
    )

    email.send()