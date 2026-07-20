from django.shortcuts import render, get_object_or_404
from dashboard.models import *
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

import uuid
import hashlib
import requests
import json
from decimal import Decimal
from threading import Thread

from website.models import HomeDonation
from receipt.views import send_donation_success_email


def generate_unique_txnid():
    while True:
        txnid = uuid.uuid4().hex
        if not (
            HomeDonation.objects.filter(txnid=txnid).exists()
        ):
            return txnid


@method_decorator(csrf_exempt, name="dispatch")
class CreateHomePaymentView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            print("RECEIVED DATA:", data)

            donor_name = data.get("donor_name", "").strip()
            donor_mobile = data.get("donor_mobile")
            donor_email = data.get("donor_email", "").strip()
            service_date = data.get("service_date") or None
            pan_number = data.get("pan_number")
            address = data.get("address")

            breakfast_selected = bool(data.get("breakfast_selected", False))
            lunch_selected = bool(data.get("lunch_selected", False))
            dinner_selected = bool(data.get("dinner_selected", False))
            lunch_type = data.get("lunch_type") or None
            total_price = data.get("total_price")

            # Validate required fields
            if not all([donor_name, donor_email, donor_mobile, total_price]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            try:
                total_amount = Decimal(total_price)
            except Exception:
                return JsonResponse({"error": "Invalid amount format"}, status=400)

            if total_amount <= 0:
                return JsonResponse({"error": "Invalid amount"}, status=400)

            txnid = generate_unique_txnid()

            home = None
            home_slug = data.get("home_slug")
            home_name = data.get("home_name")
            if home_slug:
                home = Home.objects.filter(slug=home_slug).first()
            elif home_name:
                home = Home.objects.filter(name=home_name).first()

            productinfo = "Food Donation"

            # Save donation in DB
            donation = HomeDonation.objects.create(
                home=home,
                donor_name=donor_name,
                donor_mobile=donor_mobile,
                donor_email=donor_email,
                service_date=service_date,
                pan_number=pan_number,
                address=address,
                breakfast_selected=breakfast_selected,
                lunch_selected=lunch_selected,
                dinner_selected=dinner_selected,
                lunch_type=lunch_type,
                total_price=total_amount,
                txnid=txnid,
                is_paid=False,
            )
            request.session["txnid"] = txnid
            amount = str(donation.total_price).strip()

            # Easebuzz configuration
            key = settings.EASEBUZZ_MERCHANT_KEY
            salt = settings.EASEBUZZ_SALT
            surl = request.build_absolute_uri("/food/payment/success/")
            furl = request.build_absolute_uri("/food/payment/failed/")
            hash_string = f"{key}|{txnid}|{amount}|{productinfo}|{donor_name}|{donor_email}|||||||||||{salt}"
            hash_value = hashlib.sha512(hash_string.encode("utf-8")).hexdigest().lower()

            print("SUCCESS URL:", surl)
            print("FAILED URL:", furl)

            payload = {
                "key": key,
                "txnid": txnid,
                "amount": str(amount),
                "productinfo": productinfo,
                "firstname": donor_name,
                "phone": donor_mobile,
                "email": donor_email,
                "surl": surl,
                "furl": furl,
                "hash": hash_value,
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }

            try:
                response = requests.post(
                    settings.EASEBUZZ_INITIATE_PAYMENT_URL, data=payload, headers=headers
                )
                print("STATUS CODE =", response.status_code)
                print("RAW RESPONSE =", response.text)
                result = response.json()
                print("PARSED RESPONSE =", result)

            except Exception as e:
                print("Easebuzz error:", e)
                return JsonResponse(
                    {"error": "Failed to connect with Easebuzz."}, status=500
                )

            if result.get("status") == 1 and "data" in result:
                return JsonResponse({"key": result["data"]})
            else:
                return JsonResponse({
                    "error": "Payment initiation failed",
                    "details": result
                }, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class HomeDonationCallbackView(View):

    def post(self, request):
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
            print("CALLBACK DATA:", data)

            txnid = data.get("txnid")
            status = (data.get("status") or "").lower()

            if not txnid:
                return JsonResponse({"error": "txnid missing"}, status=400)

            donation = HomeDonation.objects.filter(txnid=txnid).first()
            if not donation:
                return JsonResponse({"error": "Donation not found"}, status=404)

            if donation.is_paid:
                return JsonResponse({"status": "already_updated"})

            # Save Easebuzz data
            donation.easebuzz_transaction_id = data.get("easepayid")
            donation.easebuzz_payment_mode = data.get("mode")
            donation.easebuzz_payment_status = status

            donation.is_paid = status.lower() in ["success", "1", "txn_success"]
            donation.save()

            if donation.is_paid:
                Thread(
                    target=send_donation_success_email,
                    kwargs={
                        "donation": donation,
                        "request": request,
                        "donation_type": "home"
                    },
                    daemon=True
                ).start()

            return JsonResponse({
                "status": "ok",
                "is_paid": donation.is_paid,
                "txnid": txnid
            })

        except Exception as e:
            print("Callback Error:", str(e))
            return JsonResponse({"error": str(e)}, status=500)

    def get(self, request):
        return JsonResponse({"message": "callback working"})


class HomePaymentSuccessView(View):
    def get(self, request):

        txnid = request.GET.get("txnid") or request.session.get("txnid")

        if not txnid:
            return HttpResponse("Transaction ID missing", status=400)

        donation = HomeDonation.objects.filter(txnid=txnid).first()

        if not donation:
            return HttpResponse("Transaction not found", status=404)

        if not donation.is_paid:
            return HttpResponse("Payment not confirmed yet", status=400)

        return render(request, "website/success.html", {
            "donation": donation,
            "txnid": txnid,
            "status": "success",
            "donation_type": "home"
        })


class HomePaymentFailedView(View):
    def get(self, request):
        txnid = request.GET.get("txnid") or request.session.get("txnid")

        if not txnid:
            return HttpResponse("Transaction ID missing", status=400)

        donation = HomeDonation.objects.filter(txnid=txnid).first()

        return render(request, "website/failed.html", {
            "donation": donation,
            "txnid": txnid,
            "status": "failed",
            "donation_type": "home"
        })


def home_details(request, slug):
    home = get_object_or_404(Home, slug=slug)

    context = {
        "home": home,
        "easebuzz": {
            "merchant_key": settings.EASEBUZZ_MERCHANT_KEY,
            "env": settings.EASEBUZZ_ENV,
        }
    }

    return render(request, "website/food.html", context)


def home(request):
    context = {
        "easebuzz": {
            "merchant_key": settings.EASEBUZZ_MERCHANT_KEY,
            "env": settings.EASEBUZZ_ENV,
        }
    }

    return render(request, 'website/food.html', context)
