import threading

from django.shortcuts import render, get_object_or_404

from receipt.views import send_donation_failed_email, send_donation_success_email

from easypay.models import RMPayment


def payment_success(request):
    donor_name = request.session.get('donor_name', 'Donor')
    donor_amount = request.session.get('donor_amount')
    txnid = request.session.get('txnid')

    donation = get_object_or_404(RMPayment, txnid=txnid, is_paid=True)

    threading.Thread(
        target=send_donation_success_email,
        args=(donation, "rm", request),
    ).start()

    return render(request, 'easypay/success.html', {
        'donor_name': donor_name,
        'donor_amount': donor_amount,
        'donation_type': 'rm',
        'txnid': txnid,
        'donation': donation,
    })


def payment_failure(request):
    donor_name = request.session.get('donor_name', 'Donor')
    donor_amount = request.session.get('donor_amount')
    txnid = request.session.get('txnid')

    donation = RMPayment.objects.filter(txnid=txnid).first()

    threading.Thread(
        target=send_donation_failed_email,
        args=(donation, "rm"),
    ).start()

    return render(request, 'easypay/failed.html', {
        'donor_name': donor_name,
        'donor_amount': donor_amount,
        'donation_type': "rm",
        'txnid': txnid,
        'donation': donation,
    })
