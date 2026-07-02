import hashlib
import json
import uuid

import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from easypay.models import RMPayment


def generate_unique_rm_txnid():
    while True:
        txnid = uuid.uuid4().hex[:20]
        if not RMPayment.objects.filter(txnid=txnid).exists():
            return txnid


@method_decorator(csrf_exempt, name='dispatch')
class CreateRMPaymentView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)

            donor_name = data.get('donor_name')
            donor_email = data.get('donor_email')
            donor_mobile = data.get('donor_mobile')
            donor_amount = data.get('donor_amount')
            donor_address = data.get('donor_address')
            package_type = data.get('package_type')
            rm_code = data.get('rm_code')
            rm_name = data.get('rm_name')

            if not all([donor_name, donor_email, donor_mobile, donor_amount, package_type]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            txnid = generate_unique_rm_txnid()

            RMPayment.objects.create(
                rm_code=rm_code,
                rm_name=rm_name,
                donor_name=donor_name,
                donor_email=donor_email,
                donor_mobile=donor_mobile,
                donor_address=donor_address,
                package_type=package_type,
                donor_amount=donor_amount,
                txnid=txnid,
            )

            key = settings.EASEBUZZ_MERCHANT_KEY
            salt = settings.EASEBUZZ_SALT
            productinfo = "RM Donation"

            surl = request.build_absolute_uri(reverse('payment_success'))
            furl = request.build_absolute_uri(reverse('payment_failure'))

            hash_string = f"{key}|{txnid}|{donor_amount}|{productinfo}|{donor_name}|{donor_email}|||||||||||{salt}"
            hash_value = hashlib.sha512(hash_string.encode('utf-8')).hexdigest().lower()

            payload = {
                "key": key,
                "txnid": txnid,
                "amount": str(donor_amount),
                "productinfo": productinfo,
                "firstname": donor_name,
                "email": donor_email,
                "phone": donor_mobile,
                "surl": surl,
                "furl": furl,
                "hash": hash_value,
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }

            response = requests.post(
                settings.EASEBUZZ_INITIATE_PAYMENT_URL,
                data=payload,
                headers=headers,
            )

            result = response.json()

            access_key = None
            if "data" in result:
                if isinstance(result["data"], dict) and "access_key" in result["data"]:
                    access_key = result["data"]["access_key"]
                elif isinstance(result["data"], str):
                    access_key = result["data"]

            if access_key:
                return JsonResponse({"key": access_key})
            return JsonResponse(
                {"error": "Easebuzz did not return access_key", "raw": result},
                status=500,
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class RMPaymentCallbackView(View):
    def post(self, request):
        try:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                data = request.POST.dict()

            txnid = data.get("txnid")
            payment_status = data.get("status")

            received_hash = data.get("hash")
            salt = settings.EASEBUZZ_SALT
            key = settings.EASEBUZZ_MERCHANT_KEY
            # Easebuzz reverse-hash format:
            # salt|status|udf10|udf9|...|udf1|email|firstname|productinfo|amount|txnid|key
            # 10 empty UDFs => 11 pipes between status and email.
            reverse_hash_str = (
                f"{salt}|{payment_status}|||||||||||"
                f"{data.get('email', '')}|{data.get('firstname', '')}|"
                f"{data.get('productinfo', '')}|{data.get('amount', '')}|"
                f"{txnid}|{key}"
            )
            computed_hash = hashlib.sha512(reverse_hash_str.encode('utf-8')).hexdigest().lower()
            if not received_hash or received_hash.lower() != computed_hash:
                return JsonResponse({"error": "Invalid hash"}, status=403)

            payment_mode = data.get("payment_mode") or data.get("mode")
            easebuzz_transaction_id = data.get("easepayid") or data.get("transaction_id")
            error_message = data.get("error_Message")

            payment = get_object_or_404(RMPayment, txnid=txnid)

            payment.easebuzz_transaction_id = easebuzz_transaction_id
            payment.easebuzz_payment_mode = payment_mode
            payment.easebuzz_payment_status = payment_status

            if payment_status == "success":
                payment.is_paid = True

            payment.save()

            request.session['txnid'] = payment.txnid
            request.session['donor_name'] = payment.donor_name
            request.session['donor_amount'] = str(payment.donor_amount)
            request.session['donation_type'] = 'rm'
            request.session['payment_status'] = payment.easebuzz_payment_status
            request.session.modified = True

            if payment_status == "success":
                return JsonResponse({"status": "success"})
            return JsonResponse({"status": "failed", "error": error_message}, status=400)

        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": "Unexpected error",
                "error": str(e),
            }, status=500)
