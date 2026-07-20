DONATION_TYPE_LABELS = {
    "manual": "Manual Donation",
    "service": "Service Donation",
    "home": "Home Donation",
    "rm": "RM Donation",
}


def get_donation_name(donation, donation_type):
    if donation_type == "home":
        home = getattr(donation, "home", None)
        return getattr(home, "name", None) or "Home Donation"
    elif donation_type == "service":
        service = getattr(donation, "service", None)
        return getattr(service, "service_name", None) or "Service Donation"
    elif donation_type == "manual":
        return "Manual Donation"
    elif donation_type == "rm":
        return "RM Donation"
    return "Donation"


def has_pan(donor_pan):
    return donor_pan and donor_pan.strip()


def get_donor_pan(donation):
    donor_pan = (
        getattr(donation, "donor_pan", None)
        or getattr(donation, "pan_number", None)
        or getattr(donation, "pan_no", None)
    )
    if donor_pan:
        donor_pan = str(donor_pan).strip() or None
    return donor_pan


def get_amount(donation):
    if hasattr(donation, 'donation_price'):
        return donation.donation_price
    elif hasattr(donation, 'donation_amount'):
        return donation.donation_amount
    elif hasattr(donation, 'total_price'):
        return donation.total_price
    return 0


def get_template_name(donor_pan, donation_type=None):
    if donor_pan and donor_pan.strip():
        return "receipt/80g_receipt.html"

    return "receipt/normal_receipt.html"


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
    donor_name_clean = str(donor_name or "donor").replace(
        " ",
        "_"
    )

    if donor_pan and donor_pan.strip():
        return f"{donor_name_clean}_80g.pdf"

    return f"{donor_name_clean}.pdf"