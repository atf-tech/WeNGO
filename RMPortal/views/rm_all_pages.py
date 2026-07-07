from django.shortcuts import render
from django.utils import timezone
from datetime import datetime
from dashboard.models import RM
from RMPortal.models import Conversation as WAConv, VisitorConversation 
from RMPortal.services import expire_stale_waiting_conversations
from .auth import rm_login_required
from easypay.models import RMPayment, RMGPayPayment
from datetime import datetime, timedelta



@rm_login_required
def inbox(request):
    return render(request, 'inbox.html', {"rm": request.rm})


@rm_login_required
def whatsapp_chat(request):
    rm = request.rm
    if not rm:
        return render(request, 'whatsapp_chat.html')

    

    conversations = (
        WAConv.objects
        .filter(rm=rm)
        .select_related("donor")
        .order_by("-last_message_at")[:50]
    )

    visitor_conversations = (
        VisitorConversation.objects
        .filter(rm=rm)
        .select_related("visitor")
        .order_by("-last_message_at")[:50]
    )

    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    active_count = VisitorConversation.objects.filter(
        rm=rm, status="active",
        created_at__gte=today_start,
        created_at__lt=tomorrow_start,
    ).count()
    reassigned_count = VisitorConversation.objects.filter(
        rm=rm, status="reassigned",
        created_at__gte=today_start,
        created_at__lt=tomorrow_start,
    ).count()
    missed_count = VisitorConversation.objects.filter(
        rm=rm, status="missed",
        created_at__gte=today_start,
        created_at__lt=tomorrow_start,
    ).count()

    quickly_left_count = VisitorConversation.objects.filter(
        rm=rm, status="missed",
        missed_reason="quickly_left",
        created_at__gte=today_start,
        created_at__lt=tomorrow_start,
    ).count()

    expired = expire_stale_waiting_conversations()

    context = {
        "rm": rm,
        "conversations": conversations,
        "visitor_conversations": visitor_conversations,
        "active_count": active_count,
        "reassigned_count": reassigned_count,
        "missed_count": missed_count,
        "quickly_left_count": quickly_left_count,
    }
    return render(request, 'whatsapp_chat.html', context)



@rm_login_required
def all_transaction(request):

    rm = request.rm
    rm_code = rm.rm_code

    today = timezone.localdate()

    # Default = Today
    date_start = today
    date_end = today

    selected_date_str = request.GET.get("selected_date", "").strip()

    if selected_date_str:
        # Flatpickr (mode="range") outputs one of a few formats depending on locale/settings.
        # Support:
        #  - "05 Jul, 2026" (single date)
        #  - "05 Jul, 2026 to 08 Jul, 2026" (common)
        #  - "05 Jul, 2026 - 08 Jul, 2026" (alternate)
        try:
            normalized = selected_date_str.replace("-", " to ")
            if " to " in normalized:
                start_str, end_str = normalized.split(" to ", 1)
                date_start = datetime.strptime(start_str.strip(), "%d %b, %Y").date()
                date_end = datetime.strptime(end_str.strip(), "%d %b, %Y").date()
            else:
                date_start = datetime.strptime(normalized.strip(), "%d %b, %Y").date()
                date_end = date_start
        except ValueError:
            # If parsing fails, fall back to today while still honoring RM filtering.
            date_start = today
            date_end = today


    def matches_local_date(value):
        if value is None:
            return False
        local_value = timezone.localtime(value)
        return date_start <= local_value.date() <= date_end

    # ------------------------
    # Link Payments
    # ------------------------

    rm_payments = RMPayment.objects.filter(rm_code=rm_code).order_by("-submitted_at")
    rm_payments_list = []

    for payment in rm_payments:
        if not matches_local_date(payment.submitted_at):
            continue

        rm_payments_list.append({

            "date": payment.submitted_at,
            "source": "Link",
            "package": payment.package_type or "-",
            "amount": payment.donor_amount,
            "status": payment.easebuzz_payment_status or "-",
            "transaction_id": payment.easebuzz_transaction_id or payment.txnid,
            "payment_mode": payment.easebuzz_payment_mode or payment.payment_mode or "-",
            "donor_name": payment.donor_name,
            "donor_mobile": payment.donor_mobile,
            "donor_email": payment.donor_email,
            "donor_address": payment.donor_address or "-",
            "virtual_label": f"{payment.rm_name} - {payment.rm_code}",

        })

    # ------------------------
    # GPay Payments
    # ------------------------

    gpay_payments = RMGPayPayment.objects.filter(rm_code=rm_code).order_by("-payment_date")
    gpay_payments_list = []

    for payment in gpay_payments:
        if not matches_local_date(payment.payment_date):
            continue

        gpay_payments_list.append({

            "date": payment.payment_date,
            "source": "GPay",
            "package": payment.package_type or "-",
            "amount": payment.amount,
            "status": "Success",
            "transaction_id": payment.gpay_reference_id or "-",
            "payment_mode": payment.easebuzz_payment_mode or "-",
            "donor_name": payment.donor_name or "-",
            "donor_mobile": payment.donor_mobile or "-",
            "donor_email": payment.donor_email or "-",
            "donor_address": payment.donor_address or "-",
            "virtual_label": f"{payment.rm_name} - {payment.rm_code}",

        })

    transactions = rm_payments_list + gpay_payments_list

    transactions.sort(
        key=lambda x: x["date"],
        reverse=True
    )

    # ------------------------
    # Display Text
    # ------------------------

    if not selected_date_str:

        display = today.strftime("%d %b, %Y")
        is_default = True

    else:

        display = selected_date_str
        is_default = False

    context = {

        "rm": rm,

        "transactions": transactions,

        "selected_date_str": selected_date_str,

        "filter_start_date": date_start,

        "filter_end_date": date_end,

        "date_filter": {

            "display": display,
            "is_default": is_default,

        },

    }

    return render(request, "all_transaction.html", context)