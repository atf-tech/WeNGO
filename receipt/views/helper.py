DONATION_TYPE_LABELS = {
    "service": "Service Donation",
    "home": "Home Donation",
    # "student": "Student Donation",
    # "festival": "Festival Donation",
    # "birthday": "Birthday Donation",
    "rm": "RM Donation",
}


def has_pan(donor_pan):
    return donor_pan and donor_pan.strip()


def get_amount(donation):
    if hasattr(donation, 'donation_price'):
        return donation.donation_price
    elif hasattr(donation, 'donation_amount'):
        return donation.donation_amount
    return 0


def get_template_name(donor_pan, donation_type=None):
    if donor_pan and donor_pan.strip():
        return "receipts/80g_receipt.html"

    return "receipts/normal_receipt.html"


def get_download_identifier(donation, donation_type):
    if hasattr(donation, 'receipt_no'):
        return f"{donation_type.upper()}_{donation.receipt_no}_{donation.donor_name}"
    elif hasattr(donation, 'txnid'):
        return f"{donation_type.upper()}_{donation.txnid}"
    return f"{donation_type.upper()}_{donation.id}"


def get_date_label(donation_type):
    date_labels = {
        "service": "Service Date",
        "home": "Donation Date",
        "student": "Registration Date",
        "festival": "Event Date",
        "birthday": "Celebration Date",
        "rm": "Contribution Date",
    }
    return date_labels.get(donation_type, "Date")


def get_pdf_filename(donor_name, donor_pan=None, donation_type="manual"):
    donor_name_clean = donor_name.replace(
        " ",
        "_"
    )

    if donation_type == "manual" and donor_pan and donor_pan.strip():
        return f"{donor_name_clean}_80g.pdf"

    return f"{donor_name_clean}.pdf"