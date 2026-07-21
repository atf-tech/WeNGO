from django.shortcuts import render,redirect
from dashboard.models import Services
from django.shortcuts import render, get_object_or_404
from website.models import *
import uuid
import hashlib
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.views import View
from django.utils.decorators import method_decorator
from decimal import Decimal
from django.http import HttpResponse, JsonResponse
from receipt.views import send_donation_success_email
from threading import Thread




def generate_unique_txnid():
    while True:
        txnid = uuid.uuid4().hex
        if not (
            ServiceDonation.objects.filter(txnid=txnid).exists()
        ):
            return txnid


def service(request):

    services = Services.objects.all().order_by("display_order")

    return render(request, 'website/service.html',{"services": services})


def service_detail(request, slug):
    service = get_object_or_404(Services, slug=slug)

    context = {
        "service": service,
        "easebuzz": {
            "merchant_key": settings.EASEBUZZ_MERCHANT_KEY,
            "env": settings.EASEBUZZ_ENV,
        }
    }

    return render(request, "website/service_detail.html", context)
    

@method_decorator(csrf_exempt, name="dispatch")
class CreateServicePaymentView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            print("RECEIVED DATA:", data)

            donor_name = data.get("donor_name", "").strip()
            donor_mobile = data.get("donor_mobile")
            donor_email = data.get("donor_email", "").strip()
            service_date = data.get("service_date")or None
            pan_number = data.get("pan_number")
            address = data.get("address")
            quantity = data.get("quantity")
            donation_amount = data.get("donation_amount")

            # Validate required fields
            if not all([donor_name, donor_email, donor_mobile, donation_amount]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            try:
                donor_amount = Decimal(donation_amount)
            except Exception:
                return JsonResponse({"error": "Invalid amount format"}, status=400)

            
            print("Amount:", donor_amount)
            
            quantity_raw = data.get("quantity", 1)
            try:
                quantity = int(quantity_raw)
            except (ValueError, TypeError):
                quantity = 1

          
            txnid = generate_unique_txnid()
            slug = data.get("service_slug")

            if not slug:
                return JsonResponse({"error": "service_slug missing"}, status=400)

            service_obj = Services.objects.filter(slug=slug).first()

            if not service_obj:
                return JsonResponse({"error": "Invalid service"}, status=400)
            
            productinfo = "Service Donation"


            # Save donation in DB (including home_tag)
            donation = ServiceDonation.objects.create(
                service=service_obj,

                donor_name=donor_name,
                donor_mobile=donor_mobile,
                donor_email=donor_email,
                service_date= service_date,
                pan_number=pan_number,
                address=address,
                quantity=quantity,
                donation_amount=donation_amount,
                txnid=txnid,
                is_paid=False,
            )


            # Temp ########################
            donation.is_paid = True
            donation.easebuzz_payment_status = "verification_mode"
            donation.save()

            request.session["txnid"] = txnid
            print("TEMP VERIFICATION MODE")
            return JsonResponse({
                "status": "success",
                "redirect_url": "/payment/success/"
            })
        

            # request.session["txnid"] = txnid 
            # amount = str(donation.donation_amount).strip() 

            # # Easebuzz configuration
            # key = settings.EASEBUZZ_MERCHANT_KEY
            # salt = settings.EASEBUZZ_SALT
            # surl = request.build_absolute_uri("/payment/success/")
            # furl = request.build_absolute_uri("/payment/failed/")
            # hash_string = f"{key}|{txnid}|{amount}|{productinfo}|{donor_name}|{donor_email}|||||||||||{salt}"
            # hash_value = hashlib.sha512(hash_string.encode("utf-8")).hexdigest().lower()

            # print("SUCCESS URL:", surl)
            # print("FAILED URL:", furl)

            # payload = {
            #     "key": key,
            #     "txnid": txnid,
            #     "amount": str(amount),
            #     "productinfo": productinfo,
            #     "firstname": donor_name,
            #     "phone": donor_mobile,
            #     "email": donor_email,
            #     "surl": surl,
            #     "furl": furl,
            #     "hash": hash_value,
            # }

            # headers = {
            #     "Content-Type": "application/x-www-form-urlencoded",
            #     "Accept": "application/json",
            # }

            # try:
            #     response = requests.post(
            #         settings.EASEBUZZ_INITIATE_PAYMENT_URL, data=payload, headers=headers
            #     )
            #     print("STATUS CODE =", response.status_code)
            #     print("RAW RESPONSE =", response.text)
            #     result = response.json()
            #     print("PARSED RESPONSE =", result)

            # except Exception as e:
            #     print("Easebuzz error:", e)
            #     return JsonResponse(
            #         {"error": "Failed to connect with Easebuzz."}, status=500
            #     )

            # if result.get("status") == 1 and "data" in result:
            #     return JsonResponse({"key": result["data"]})
            # else:
            #     return JsonResponse({
            #         "error": "Payment initiation failed",
            #         "details": result
            #     }, status=400)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        


        
@method_decorator(csrf_exempt, name="dispatch")
class ServiceDonationCallbackView(View):

    def post(self, request):
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
            print("CALLBACK DATA:", data)

            txnid = data.get("txnid")
            status = (data.get("status") or "").lower()

            if not txnid:
                return JsonResponse({"error": "txnid missing"}, status=400)

            donation = ServiceDonation.objects.filter(txnid=txnid).first()
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
                        "donation_type": "service"
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

    
           

class PaymentSuccessView(View):
    def get(self, request):

        txnid = request.GET.get("txnid") or request.session.get("txnid")

        if not txnid:
            return HttpResponse("Transaction ID missing", status=400)

        donation = ServiceDonation.objects.filter(txnid=txnid).first()


        if not donation:
            return HttpResponse("Transaction not found", status=404)

        if not donation.is_paid:
            return HttpResponse("Payment not confirmed yet", status=400)

        return render(request, "website/success.html", {
            "donation": donation,
            "txnid": txnid,
            "status": "success",
            "donation_type": "service"
        })
    

class PaymentFailedView(View):
    def get(self, request):
        txnid = request.GET.get("txnid") or request.session.get("txnid")

        if not txnid:
            return HttpResponse("Transaction ID missing", status=400)

        donation = ServiceDonation.objects.filter(txnid=txnid).first()

        return render(request, "website/failed.html", {
            "donation": donation,
            "txnid": txnid,
            "status": "failed"
        })