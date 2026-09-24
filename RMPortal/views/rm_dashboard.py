from __future__ import annotations
from datetime import date, datetime, timedelta
from django.db.models import Sum, Q
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from dashboard.models import RM
from easypay.models import RMPayment, RMGPayPayment
from receipt.views.success_mail import send_donation_success_email
import json



def _start_of_day(d: date):
    return timezone.make_aware(
        datetime.combine(d, datetime.min.time()), timezone.get_current_timezone()
    )


def _end_of_day(d: date):
    return timezone.make_aware(
        datetime.combine(d, datetime.max.time()), timezone.get_current_timezone()
    )


def _start_of_month(d: date):
    d0 = d.replace(day=1)
    return _start_of_day(d0)


def _end_of_month(d: date):
    if d.month == 12:
        d1 = d.replace(year=d.year + 1, month=1, day=1)
    else:
        d1 = d.replace(month=d.month + 1, day=1)
    return _end_of_day(d1 - timedelta(days=1))


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1

    # Clamp day to last day of target month
    last_day = (date(year, month, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    day = min(d.day, last_day.day)
    return d.replace(year=year, month=month, day=day)



def _sum_decimal(qs, field_name: str) -> float:
    val = qs.aggregate(total=Sum(field_name))["total"]
    return float(val or 0)


def _successful_rm_link_qs(rm: RM, start_dt, end_dt):
    # RMPayment: paid records are marked with is_paid=True and exclude failed-like statuses.
    # We keep this conservative.
    return RMPayment.objects.filter(
        rm_code=rm.rm_code,
        is_paid=True,
        submitted_at__gte=start_dt,
        submitted_at__lte=end_dt,
    )


def _successful_rm_gpay_qs(rm: RM, start_dt, end_dt):
    return RMGPayPayment.objects.filter(
        rm_code=rm.rm_code,
        payment_date__gte=start_dt,
        payment_date__lte=end_dt,
    )




def _weekday_monday_first(d: date) -> date:

    return d - timedelta(days=d.weekday())


# ──────────────────────────────────────────────────────────
# Friendly Search Q builders
# ──────────────────────────────────────────────────────────
def _build_link_search_q(search_term: str) -> Q:
    """Build a Q() object that searches across all important RMPayment fields."""
    q = Q()
    # String/char fields - __icontains works
    for field in [
        "receipt_no__icontains",
        "donor_name__icontains",
        "donor_mobile__icontains",
        "donor_email__icontains",
        "donor_address__icontains",
        "pan_no__icontains",
        "rm_name__icontains",
        "rm_code__icontains",
        "package_type__icontains",
        "easebuzz_payment_status__icontains",
        "easebuzz_payment_mode__icontains",
        "payment_mode__icontains",
    ]:
        q |= Q(**{field: search_term})
    # DecimalField - convert to string for search using exact match on string
    # Only search amount if search term is numeric
    if search_term.replace('.', '', 1).replace('-', '', 1).isdigit():
        q |= Q(donor_amount=search_term)
    return q


def _build_gpay_search_q(search_term: str) -> Q:
    """Build a Q() object that searches across all important RMGPayPayment fields."""
    q = Q()
    for field in [
        "receipt_no__icontains",
        "donor_name__icontains",
        "donor_mobile__icontains",
        "donor_email__icontains",
        "donor_address__icontains",
        "donor_pan__icontains",
        "rm_name__icontains",
        "rm_code__icontains",
        "package_type__icontains",
        "gpay_reference_id__icontains",
    ]:
        q |= Q(**{field: search_term})
    # DecimalField - only search amount if search term is numeric
    if search_term.replace('.', '', 1).replace('-', '', 1).isdigit():
        q |= Q(amount=search_term)
    return q


def rmportal_index(request, rm_code=None):

    rm = getattr(request, "rm", None)
    if not rm:
        # RMAuthMiddleware sets request.rm_id; treat it as rm_code
        rm_id = getattr(request, "rm_id", None)
        if rm_id:
            rm = RM.objects.filter(rm_code=rm_id).first()

    # Fallback: if URL provided rm_code explicitly, use it
    if not rm and rm_code:
        rm = RM.objects.filter(rm_code=rm_code).first()

    if not rm:
        return render(request, "RMPortal/index.html")

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    this_month_start = _start_of_month(today).date()
    this_month_end = _end_of_month(today).date()

    last_month_date = _add_months(today.replace(day=1), -1)
    last_month_start = _start_of_month(last_month_date).date()
    last_month_end = _end_of_month(last_month_date).date()

    start_today = _start_of_day(today)
    end_today = _end_of_day(today)
    start_yesterday = _start_of_day(yesterday)
    end_yesterday = _end_of_day(yesterday)

    start_this_month = _start_of_day(this_month_start)
    end_this_month = _end_of_day(this_month_end)

    start_last_month = _start_of_day(last_month_start)
    end_last_month = _end_of_day(last_month_end)

    link_today_qs = _successful_rm_link_qs(rm, start_today, end_today)
    gpay_today_qs = _successful_rm_gpay_qs(rm, start_today, end_today)

    print("All RM Codes in DB:")
    print(list(RMPayment.objects.values_list("rm_code", flat=True).distinct()))

    print("=" * 50)
    print("Dashboard RM Code:", rm.rm_code)

    print("Link Count:", link_today_qs.count())
    print("GPay Count:", gpay_today_qs.count())

    print("Link Amount:", _sum_decimal(link_today_qs, "donor_amount"))
    print("GPay Amount:", _sum_decimal(gpay_today_qs, "amount"))

    link_yesterday_qs = _successful_rm_link_qs(rm, start_yesterday, end_yesterday)
    gpay_yesterday_qs = _successful_rm_gpay_qs(rm, start_yesterday, end_yesterday)

    # Totals
    today_link_amount = _sum_decimal(link_today_qs, "donor_amount")
    print("=" * 50)
    print("RM Code:", rm.rm_code)

    print("Link Today Count:", link_today_qs.count())
    print("Link Today Amount:", today_link_amount)

    print("Link SQL:")
    print(link_today_qs.query)
    today_gpay_amount = _sum_decimal(gpay_today_qs, "amount")
    print("=" * 50)

    print("GPay Today Count:", gpay_today_qs.count())
    print("GPay Today Amount:", today_gpay_amount)

    print(gpay_today_qs.query)
    today_total_amount = today_link_amount + today_gpay_amount 

    yesterday_link_amount = _sum_decimal(link_yesterday_qs, "donor_amount")
    yesterday_gpay_amount = _sum_decimal(gpay_yesterday_qs, "amount")
    yesterday_total_amount = yesterday_link_amount + yesterday_gpay_amount 

    # Monthly totals
    link_this_month_qs = _successful_rm_link_qs(rm, start_this_month, end_this_month)
    gpay_this_month_qs = _successful_rm_gpay_qs(rm, start_this_month, end_this_month)

    link_last_month_qs = _successful_rm_link_qs(rm, start_last_month, end_last_month)
    gpay_last_month_qs = _successful_rm_gpay_qs(rm, start_last_month, end_last_month)

    this_month_amount = (
        _sum_decimal(link_this_month_qs, "donor_amount")
        + _sum_decimal(gpay_this_month_qs, "amount")
    )

    last_month_amount = (
        _sum_decimal(link_last_month_qs, "donor_amount")
        + _sum_decimal(gpay_last_month_qs, "amount")
    )

    # Counts for collection cards
    today_total_donations = link_today_qs.count() + gpay_today_qs.count() 

    # Growth percentages (simple comparison vs previous day/month)
    def _growth_pct(current: float, previous: float) -> float:
        if previous <= 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100.0

    today_growth_pct = _growth_pct(today_total_amount, yesterday_total_amount)
    this_month_growth_pct = _growth_pct(this_month_amount, last_month_amount)

    link_collected = _sum_decimal(
        RMPayment.objects.filter(
            rm_code=rm.rm_code,
            is_paid=True,
        ),
        "donor_amount",
    )

    gpay_collected = _sum_decimal(
        RMGPayPayment.objects.filter(
            rm_code=rm.rm_code,
        ),
        "amount",
    )

    rm_collected_amount = link_collected + gpay_collected

    target = float(rm.target_amount or 0)

    if target > 0:
        collected_percent = round((rm_collected_amount / target) * 100, 2)

        if collected_percent >= 100:
            payment_status = "completed"
        elif collected_percent > 0:
            payment_status = "progressing"
        else:
            payment_status = "pending"
    else:
        collected_percent = 0
        payment_status = "pending"

    # =====================================================
    # Today Hourly Collection (24 Hours)
    # Link + GPay
    # =====================================================

    hourly_values = []
    hourly_link_values = []
    hourly_gpay_values = []

    for hour in range(24):

        hour_start = timezone.make_aware(
            datetime.combine(today, datetime.min.time())
        ) + timedelta(hours=hour)

        hour_end = hour_start + timedelta(hours=1)

        link_amount = (
            RMPayment.objects.filter(
                rm_code=rm.rm_code,
                is_paid=True,
                submitted_at__gte=hour_start,
                submitted_at__lt=hour_end,
            ).aggregate(total=Sum("donor_amount"))["total"] or 0
        )

        gpay_amount = (
            RMGPayPayment.objects.filter(
                rm_code=rm.rm_code,
                payment_date__gte=hour_start,
                payment_date__lt=hour_end,
            ).aggregate(total=Sum("amount"))["total"] or 0
        )

        hourly_link_values.append(float(link_amount))
        hourly_gpay_values.append(float(gpay_amount))

        hourly_values.append(float(link_amount + gpay_amount))

    # Weekly chart (Monday..Sunday) for today week based chart
    week_start = _weekday_monday_first(today)
    week_categories = []
    week_values = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        s = _start_of_day(d)
        e = _end_of_day(d)
        amt = (
            _sum_decimal(_successful_rm_link_qs(rm, s, e), "donor_amount")
            + _sum_decimal(_successful_rm_gpay_qs(rm, s, e), "amount")
        )
        week_categories.append(d.strftime("%A"))
        week_values.append(amt)

    # Monthly chart daily totals for selected/current month

    month_categories = []
    month_values = []

    first_day = today.replace(day=1)
    last_day = _end_of_month(today).date()

    current = first_day
    week_no = 1

    while current <= last_day:

        week_end = min(current + timedelta(days=6), last_day)

        amount = (
            _sum_decimal(
                _successful_rm_link_qs(
                    rm,
                    _start_of_day(current),
                    _end_of_day(week_end),
                ),
                "donor_amount",
            )
            +
            _sum_decimal(
                _successful_rm_gpay_qs(
                    rm,
                    _start_of_day(current),
                    _end_of_day(week_end),
                ),
                "amount",
            )
        )

        month_categories.append(f"Week {week_no}")
        month_values.append(amount)

        current = week_end + timedelta(days=1)
        week_no += 1

 


    # =====================================================
    # Date Filter & Friendly Search Implementation
    # =====================================================

    # Parse GET parameters (only for initial page load)
    date_from_str = request.GET.get("date_from", "").strip()
    date_to_str = request.GET.get("date_to", "").strip()
    search_term = request.GET.get("search", "").strip()

    # Determine date range for table filtering
    if date_from_str and date_to_str:
        try:
            filter_date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
            filter_date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        except ValueError:
            filter_date_from = today
            filter_date_to = today
    else:
        filter_date_from = today
        filter_date_to = today

    filter_start_dt = _start_of_day(filter_date_from)
    filter_end_dt = _end_of_day(filter_date_to)

    # Build donations list
    donations = _get_filtered_donations(rm, filter_start_dt, filter_end_dt, search_term)

    payment_link = request.build_absolute_uri(f"/easepay/{rm.rm_code}/")

    # Build display strings for frontend
    is_default_filter = not (date_from_str and date_to_str) and not search_term
    if is_default_filter:
        filter_display = today.strftime("%d/%m/%Y")
    elif date_from_str and date_to_str:
        if date_from_str == date_to_str:
            filter_display = datetime.strptime(date_from_str, "%Y-%m-%d").strftime("%d/%m/%Y")
        else:
            fd = datetime.strptime(date_from_str, "%Y-%m-%d").strftime("%d %b, %Y")
            td = datetime.strptime(date_to_str, "%Y-%m-%d").strftime("%d %b, %Y")
            filter_display = f"{fd} → {td}"
    else:
        filter_display = today.strftime("%d/%m/%Y")

    context = {
        "rm": rm,

        "rm_name": rm.rm_name,
        "rm_mobile": rm.rm_mob_no,
        "rm_email": rm.rm_email,
        "payment_link": payment_link,
        "rm_virtual_label": f"{rm.rm_name} - {rm.rm_code}",

        "hourly_values": hourly_values,
        "hourly_link_values": hourly_link_values,
        "hourly_gpay_values": hourly_gpay_values,

        "week_categories": json.dumps(week_categories),
        "week_values": json.dumps(week_values),
        

        "target": target,
        "payment_status": payment_status,
        "rm_collected_amount": rm_collected_amount,
        "collected_percent": collected_percent,
        "today_collection_amount": today_total_amount,
        "today_collection_growth_pct": today_growth_pct,
        "today_link_collection_amount": today_link_amount,
        "today_gpay_collection_amount": today_gpay_amount,
        "yesterday_collection_amount": yesterday_total_amount,
        "this_month_collection_amount": this_month_amount,
        "last_month_collection_amount": last_month_amount,
        "this_month_growth_pct": this_month_growth_pct,

        "week_categories": week_categories,
        "week_values": week_values,

        "month_categories": json.dumps(month_categories),
        "month_values": json.dumps(month_values),  
        
        "donations": donations,
        "today": today,

        # Filter state for frontend
        "filter_date_from": date_from_str if date_from_str else "",
        "filter_date_to": date_to_str if date_to_str else "",
        "filter_search": search_term,
        "filter_display": filter_display,
        "is_default_filter": is_default_filter,
    }

    return render(request, "RMPortal/index.html", context)


# ──────────────────────────────────────────────────────────
# Shared filtered-donations queryset logic (used by page load & AJAX)
# ──────────────────────────────────────────────────────────
def _get_filtered_donations(rm, filter_start_dt, filter_end_dt, search_term=""):
    """Return a list of donation dicts filtered by date + optional friendly search."""
    donations = []

    # RMPayment (Link)
    link_base_qs = RMPayment.objects.filter(
        rm_code=rm.rm_code,
        is_paid=True,
        submitted_at__gte=filter_start_dt,
        submitted_at__lte=filter_end_dt,
    )
    if search_term:
        link_base_qs = link_base_qs.filter(_build_link_search_q(search_term))
    link_qs = link_base_qs.order_by("-submitted_at")

    for p in link_qs:
        donor_complete = bool(p.donor_name and p.donor_mobile and p.donor_email)
        donations.append({
            "donation_id": f"link-{p.id}",
            "sort_key": p.submitted_at,
            "submitted_at": timezone.localtime(p.submitted_at).strftime("%d %b, %Y %I:%M %p") if p.submitted_at else "-",
            "source": "Link",
            "package_type": p.package_type or "-",
            "amount": float(p.donor_amount),
            "status": p.easebuzz_payment_status or p.payment_status or "success",
            "mode": p.easebuzz_payment_mode or p.payment_mode or "-",
            "ptid": p.easebuzz_transaction_id or p.txnid or "-",
            "uqid": p.txnid or "-",
            "donor_name": p.donor_name or "-",
            "donor_mobile": p.donor_mobile or "-",
            "donor_email": p.donor_email or "-",
            "donor_address": p.donor_address or "-",
            "receipt_no": p.receipt_no or "-",
            "virtual_label": f"{p.rm_name} - {p.rm_code}",
            "pan_no": p.pan_no or "",
            "rm_name": p.rm_name,
            "rm_code": p.rm_code,
            "donor_complete": donor_complete,
        })

    # RMGPayPayment (GPay)
    gpay_base_qs = RMGPayPayment.objects.filter(
        rm_code=rm.rm_code,
        payment_date__gte=filter_start_dt,
        payment_date__lte=filter_end_dt,
    )
    if search_term:
        gpay_base_qs = gpay_base_qs.filter(_build_gpay_search_q(search_term))
    gpay_qs = gpay_base_qs.order_by("-payment_date")

    for p in gpay_qs:
        donor_complete = bool(p.donor_name and p.donor_mobile and p.donor_email)
        donations.append({
            "donation_id": f"gpay-{p.id}",
            "sort_key": p.payment_date,
            "submitted_at": timezone.localtime(p.payment_date).strftime("%d %b, %Y %I:%M %p") if p.payment_date else "-",
            "source": "GPay",
            "package_type": p.package_type or "-",
            "amount": float(p.amount),
            "status": "Success",
            "mode": "GPay",
            "ptid": p.gpay_reference_id or "-",
            "uqid": p.gpay_reference_id or "-",
            "donor_name": p.donor_name or "-",
            "donor_mobile": p.donor_mobile or "-",
            "donor_email": p.donor_email or "-",
            "donor_address": p.donor_address or "-",
            "receipt_no": p.receipt_no or "-",
            "virtual_label": f"{p.rm_name} - {p.rm_code}",
            "pan_no": p.donor_pan or "",
            "rm_name": p.rm_name,
            "rm_code": p.rm_code,
            "donor_complete": donor_complete,
        })

    # Sort by sort_key descending
    donations.sort(key=lambda d: d["sort_key"] or datetime.min, reverse=True)
    return donations


# ──────────────────────────────────────────────────────────
# AJAX: Filter Donations (no page reload)
# ──────────────────────────────────────────────────────────
import json as json_module

def ajax_filter_donations(request, rm_code):
    """Return JSON with filtered donations for smooth AJAX updates."""
    rm = RM.objects.filter(rm_code=rm_code).first()
    if not rm:
        return JsonResponse({"error": "RM not found"}, status=404)

    date_from_str = request.GET.get("date_from", "").strip()
    date_to_str = request.GET.get("date_to", "").strip()
    search_term = request.GET.get("search", "").strip()

    today = timezone.localdate()

    if date_from_str and date_to_str:
        try:
            filter_date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
            filter_date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        except ValueError:
            filter_date_from = today
            filter_date_to = today
    else:
        filter_date_from = today
        filter_date_to = today

    filter_start_dt = _start_of_day(filter_date_from)
    filter_end_dt = _end_of_day(filter_date_to)

    donations = _get_filtered_donations(rm, filter_start_dt, filter_end_dt, search_term)

    # Build display string
    if date_from_str and date_to_str:
        if date_from_str == date_to_str:
            filter_display = datetime.strptime(date_from_str, "%Y-%m-%d").strftime("%d/%m/%Y")
        else:
            fd = datetime.strptime(date_from_str, "%Y-%m-%d").strftime("%d %b, %Y")
            td = datetime.strptime(date_to_str, "%Y-%m-%d").strftime("%d %b, %Y")
            filter_display = f"{fd} → {td}"
    else:
        filter_display = today.strftime("%d/%m/%Y")

    return JsonResponse({
        "donations": donations,
        "total_count": len(donations),
        "filter_display": filter_display,
    })


# ──────────────────────────────────────────────────────────
# Update Donation (used by editDonation modal)
# ──────────────────────────────────────────────────────────
@require_POST
def update_donation(request):
    donation_id = request.POST.get("donation_id", "").strip()
    source = request.POST.get("donation_source", "").strip()

    donor_name = request.POST.get("donor_name", "").strip()
    donor_mobile = request.POST.get("donor_mobile", "").strip()
    donor_email = request.POST.get("donor_email", "").strip()
    donor_address = request.POST.get("donor_address", "").strip()
    donor_package = request.POST.get("donor_package", "").strip()
    pan_no = request.POST.get("pan_no", "").strip()

    if not donation_id or not source:
        return JsonResponse({"success": False, "error": "Missing donation ID or source"}, status=400)

    if source.lower() == "link":
        # donation_id format: "link-{id}"
        try:
            pk = int(donation_id.replace("link-", ""))
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid donation ID"}, status=400)
        donation = get_object_or_404(RMPayment, pk=pk)
        update_fields = []
        if donor_name:
            donation.donor_name = donor_name
            update_fields.append("donor_name")
        if donor_mobile:
            donation.donor_mobile = donor_mobile
            update_fields.append("donor_mobile")
        if donor_email:
            donation.donor_email = donor_email
            update_fields.append("donor_email")
        donation.donor_address = donor_address or donation.donor_address
        update_fields.append("donor_address")
        if donor_package:
            donation.package_type = donor_package
            update_fields.append("package_type")
        donation.pan_no = pan_no if pan_no else None
        update_fields.append("pan_no")
        donation.save(update_fields=update_fields)

    elif source.lower() == "gpay":
        try:
            pk = int(donation_id.replace("gpay-", ""))
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid donation ID"}, status=400)
        donation = get_object_or_404(RMGPayPayment, pk=pk)
        update_fields = []
        if donor_name:
            donation.donor_name = donor_name
            update_fields.append("donor_name")
        if donor_mobile:
            donation.donor_mobile = donor_mobile
            update_fields.append("donor_mobile")
        if donor_email:
            donation.donor_email = donor_email
            update_fields.append("donor_email")
        donation.donor_address = donor_address or donation.donor_address
        update_fields.append("donor_address")
        donation.donor_pan = pan_no if pan_no else None
        update_fields.append("donor_pan")
        if donor_package:
            donation.package_type = donor_package
            update_fields.append("package_type")
        donation.save(update_fields=update_fields)

    else:
        return JsonResponse({"success": False, "error": f"Unknown source: {source}"}, status=400)

    return JsonResponse({"success": True, "receipt_no": donation.receipt_no, "source": source})


# ──────────────────────────────────────────────────────────
# Send Donation Receipt Email (used by send-email-btn)
# ──────────────────────────────────────────────────────────
@require_POST
def send_donation_email(request):
    donation_id = request.POST.get("donation_id", "").strip()
    source = request.POST.get("donation_source", "").strip()

    if not donation_id or not source:
        return JsonResponse({"success": False, "error": "Missing donation ID or source"}, status=400)

    if source.lower() == "link":
        try:
            pk = int(donation_id.replace("link-", ""))
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid donation ID"}, status=400)
        donation = get_object_or_404(RMPayment, pk=pk)
    elif source.lower() == "gpay":
        try:
            pk = int(donation_id.replace("gpay-", ""))
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid donation ID"}, status=400)
        donation = get_object_or_404(RMGPayPayment, pk=pk)
    else:
        return JsonResponse({"success": False, "error": f"Unknown source: {source}"}, status=400)

    try:
        send_donation_success_email(donation, request, "rm")
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ──────────────────────────────────────────────────────────
# Download Receipt PDF (used by receipt-download-btn)
# ──────────────────────────────────────────────────────────
from receipt.views.generate_pdf import generate_donation_pdf, get_donation_pdf_filename
from django.http import HttpResponse

@require_POST
def download_receipt(request):
    donation_id = request.POST.get("donation_id", "").strip()
    source = request.POST.get("donation_source", "").strip()

    if not donation_id or not source:
        return JsonResponse({"success": False, "error": "Missing donation ID or source"}, status=400)

    if source.lower() == "link":
        try:
            pk = int(donation_id.replace("link-", ""))
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid donation ID"}, status=400)
        donation = get_object_or_404(RMPayment, pk=pk)
    elif source.lower() == "gpay":
        try:
            pk = int(donation_id.replace("gpay-", ""))
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid donation ID"}, status=400)
        donation = get_object_or_404(RMGPayPayment, pk=pk)
    else:
        return JsonResponse({"success": False, "error": f"Unknown source: {source}"}, status=400)

    try:
        pdf_file = generate_donation_pdf(donation, "rm")
        filename = get_donation_pdf_filename(donation, "rm")
        response = HttpResponse(pdf_file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

