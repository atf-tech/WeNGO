from django.shortcuts import render
from django.http import JsonResponse

from datetime import timedelta
import calendar
import json
from collections import defaultdict
from django.db.models import Sum
from django.utils import timezone
from dashboard.models import RM
from easypay.models import RMGPayPayment, RMPayment
from datetime import datetime

def _start_of_day(d):
    return timezone.make_aware(
        timezone.datetime.combine(
            d,
            timezone.datetime.min.time(),
        ),
        timezone.get_current_timezone(),
    )


def _start_of_month(d):
    return _start_of_day(d.replace(day=1))


def _add_months(d, months):
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return d.replace(year=year, month=month, day=day)



def _parse_date_from_str(date_str: str):
    date_str = (date_str or "").strip()
    if not date_str:
        return None

    fmt_candidates = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d %b, %Y",
        "%d %B, %Y",
        "%d/%m/%Y",
    ]

    last_err = None
    for fmt in fmt_candidates:
        try:
            return datetime.strptime(date_str, fmt).date()
        except Exception as e:
            last_err = e

    raise ValueError(f"Unsupported date format: {date_str!r}. Last error: {last_err}")


def _parse_selected_date_range(selected_date: str):
    """Return (start_dt, end_dt_exclusive) based on qr_donation behavior."""
    selected_date = (selected_date or "").strip()
    if not selected_date:
        return None

    # Support both:
    # - "01 Jul, 2026 - 04 Jul, 2026"
    # - "01 Jul, 2026 to 04 Jul, 2026"
    if " - " in selected_date:
        start_part, end_part = selected_date.split(" - ", 1)
    elif " to " in selected_date:
        start_part, end_part = selected_date.split(" to ", 1)
    else:
        start_part = selected_date
        end_part = selected_date

    start_part = start_part.strip()
    end_part = end_part.strip()
    if not start_part or not end_part:
        return None

    try:
        start_date = datetime.strptime(start_part, "%d %b, %Y").date()
        end_date = datetime.strptime(end_part, "%d %b, %Y").date()
    except (ValueError, TypeError):
        # Keep behavior conservative: return None if format doesn't match qr_donation.
        return None

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    start_dt = _start_of_day(start_date)
    end_dt_exclusive = _start_of_day(end_date + timedelta(days=1))
    return start_dt, end_dt_exclusive


def _parse_rm_codes(request):
    """Multi-RM support.

    Accepts:
    - rm_code=all or empty => None (no restriction)
    - rm_code=RM001 => [RM001]
    - rm_code=RM001,RM005 => [RM001, RM005]
    - multiple rm_code params (request.GET.getlist) => combined set
    """
    raw_values = []
    try:
        raw_values = request.GET.getlist("rm_code")
    except Exception:
        # Fallback if getlist isn't supported for some reason.
        raw_values = [request.GET.get("rm_code", "")] if request.GET.get("rm_code") is not None else []

    # Flatten comma-separated chunks.
    codes = []
    for v in raw_values:
        if v is None:
            continue
        v = str(v).strip()
        if not v:
            continue
        codes.extend([c.strip() for c in v.split(",") if c.strip()])

    if not codes:
        return None

    # Treat "all" as no restriction.
    if any(c.lower() == "all" for c in codes):
        return None

    # Preserve distinct codes order.
    seen = set()
    ordered = []
    for c in codes:
        if c not in seen:
            ordered.append(c)
            seen.add(c)
    return ordered


def _build_active_date_range(request):
    """Single source of truth for date filtering."""
    today = timezone.localdate()

    # 1) If top picker sends selected_date, use qr_donation parsing.
    selected_date = request.GET.get("selected_date", "").strip()
    parsed = _parse_selected_date_range(selected_date)
    if parsed:
        return parsed

    # 2) If donation picker sends date_from/date_to, interpret as inclusive days.
    date_from = (request.GET.get("date_from", "") or "").strip()
    date_to = (request.GET.get("date_to", "") or "").strip()

    df = _parse_date_from_str(date_from) if date_from else None
    dt = _parse_date_from_str(date_to) if date_to else None

    if df and dt:
        if df > dt:
            df, dt = dt, df
        return _start_of_day(df), _start_of_day(dt + timedelta(days=1))
    if df and not dt:
        return _start_of_day(df), _start_of_day(df + timedelta(days=1))
    if dt and not df:
        return _start_of_day(dt), _start_of_day(dt + timedelta(days=1))

    # 3) Default: today only.
    return _start_of_day(today), _start_of_day(today + timedelta(days=1))


def _build_filtered_querysets(request):
    """Return (link_qs, gpay_qs) filtered by the same RM+Date constraints."""
    active_start_dt, active_end_exclusive_dt = _build_active_date_range(request)
    rm_codes = _parse_rm_codes(request)

    link_base_qs = RMPayment.objects.all()
    gpay_base_qs = RMGPayPayment.objects.all()

    if rm_codes:
        link_base_qs = link_base_qs.filter(rm_code__in=rm_codes)
        gpay_base_qs = gpay_base_qs.filter(rm_code__in=rm_codes)

    link_qs = link_base_qs.filter(
        submitted_at__gte=active_start_dt,
        submitted_at__lt=active_end_exclusive_dt,
    )

    gpay_qs = gpay_base_qs.filter(
        payment_date__gte=active_start_dt,
        payment_date__lt=active_end_exclusive_dt,
    )

    return link_qs, gpay_qs



def _filtered_totals(link_qs, gpay_qs):
    filtered_link_total = link_qs.aggregate(total=Sum("donor_amount"))["total"] or 0
    filtered_gpay_total = gpay_qs.aggregate(total=Sum("amount"))["total"] or 0
    filtered_total = filtered_link_total + filtered_gpay_total

    filtered_link_count = link_qs.count()
    filtered_gpay_count = gpay_qs.count()
    filtered_total_count = filtered_link_count + filtered_gpay_count

    return (
        filtered_link_total,
        filtered_gpay_total,
        filtered_total,
        filtered_link_count,
        filtered_gpay_count,
        filtered_total_count,
    )


def RM_Portal(request):
    # If the request is made via AJAX/fetch, return JSON for the selected filters.
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1":
        today = timezone.localdate()

        # Single source of truth for filtering:
        # - Same logic as qr_donation(): build active (start_dt, end_dt_exclusive)
        # - Apply RM filter (multi-RM supported)
        link_qs, gpay_qs = _build_filtered_querysets(request)

        (
            filtered_link_total,
            filtered_gpay_total,
            filtered_total,
            filtered_link_count,
            filtered_gpay_count,
            filtered_total_count,
        ) = _filtered_totals(link_qs, gpay_qs)

        # Build card-time breakups from the SAME filtered querysets.
        start_today = _start_of_day(today)
        start_tomorrow = _start_of_day(today + timedelta(days=1))
        start_yesterday = _start_of_day(today - timedelta(days=1))

        start_this_month = _start_of_month(today)
        start_next_month = _start_of_day(_add_months(today, 1).replace(day=1))
        start_last_month = _start_of_month(_add_months(today.replace(day=1), -1))

        rm_codes = _parse_rm_codes(request)

        card_link_qs = RMPayment.objects.all()
        card_gpay_qs = RMGPayPayment.objects.all()

        # RM filter mattum apply pannanum.
        if rm_codes:
            card_link_qs = card_link_qs.filter(rm_code__in=rm_codes)
            card_gpay_qs = card_gpay_qs.filter(rm_code__in=rm_codes)

        today_link_qs = card_link_qs.filter(
            submitted_at__gte=start_today,
            submitted_at__lt=start_tomorrow,
        )

        today_gpay_qs = card_gpay_qs.filter(
            payment_date__gte=start_today,
            payment_date__lt=start_tomorrow,
        )


        yesterday_link_qs = card_link_qs.filter(
            submitted_at__gte=start_yesterday,
            submitted_at__lt=start_today,
        )

        yesterday_gpay_qs = card_gpay_qs.filter(
            payment_date__gte=start_yesterday,
            payment_date__lt=start_today,
        )


        selected_range = _build_active_date_range(request)
        selected_end = selected_range[1] - timedelta(days=1)
        selected_date = timezone.localtime(selected_end).date()
        
        month_start = _start_of_month(selected_date)
        
        this_month_link_qs = card_link_qs.filter(
            submitted_at__gte=month_start,
            submitted_at__lt=_start_of_day(selected_date + timedelta(days=1)),
        )
        
        this_month_gpay_qs = card_gpay_qs.filter(
            payment_date__gte=month_start,
            payment_date__lt=_start_of_day(selected_date + timedelta(days=1)),
        )

        last_month_link_qs = link_qs.filter(submitted_at__gte=start_last_month, submitted_at__lt=start_this_month)
        last_month_gpay_qs = gpay_qs.filter(payment_date__gte=start_last_month, payment_date__lt=start_this_month)


        today_collection = (today_link_qs.aggregate(total=Sum("donor_amount"))["total"] or 0) + (today_gpay_qs.aggregate(total=Sum("amount"))["total"] or 0)
        yesterday_collection = (yesterday_link_qs.aggregate(total=Sum("donor_amount"))["total"] or 0) + (yesterday_gpay_qs.aggregate(total=Sum("amount"))["total"] or 0)
        this_month_collection = (this_month_link_qs.aggregate(total=Sum("donor_amount"))["total"] or 0) + (this_month_gpay_qs.aggregate(total=Sum("amount"))["total"] or 0)
        last_month_collection = (last_month_link_qs.aggregate(total=Sum("donor_amount"))["total"] or 0) + (last_month_gpay_qs.aggregate(total=Sum("amount"))["total"] or 0)

        # Donations table: MUST match the same filtered querysets.
        donations = []
        for payment in link_qs.order_by("-submitted_at"):
            donations.append({
                "date": payment.submitted_at.strftime("%d-%m-%Y")
                    if payment.submitted_at else "-",
                "virtual_label": f"{payment.rm_name} - {payment.rm_code}",
                "source": "Link",
                "amount": payment.donor_amount,
                "submitted_at": timezone.localtime(payment.submitted_at).strftime("%d-%m-%Y %I:%M %p")
                    if payment.submitted_at else "-",
                "status": payment.easebuzz_payment_status or "unsettled",
                "mode": payment.easebuzz_payment_mode or payment.payment_mode or "-",
                "ptid": payment.easebuzz_transaction_id or payment.txnid or "-",
                "donor_name": payment.donor_name,
                "donor_mobile": payment.donor_mobile,
                "donor_email": payment.donor_email,
                "donor_address": payment.donor_address,
                "uqid": payment.txnid or "-",
                "receipt_no": payment.receipt_no,
            })
        for payment in gpay_qs.order_by("-payment_date"):
            donations.append({
                "date": payment.payment_date.strftime("%d-%m-%Y")
                    if payment.payment_date else "-",
                "virtual_label": f"{payment.rm_name} - {payment.rm_code}",
                "source": "GPay",
                "amount": payment.amount,
                "submitted_at": timezone.localtime(payment.payment_date).strftime("%d-%m-%Y %I:%M %p")
                    if payment.payment_date else "-",
                "status": "Success",
                "mode": "UPI",
                "ptid": payment.gpay_reference_id or "-",
                "donor_name": payment.donor_name,
                "donor_mobile": payment.donor_mobile,
                "donor_email": payment.donor_email,
                "donor_address": payment.donor_address,
                "uqid": payment.gpay_reference_id or "-",
                "receipt_no": payment.receipt_no,
            })

        donations.sort(key=lambda d: d.get("submitted_at") or d.get("date"), reverse=True)

        # Charts: keep existing keys to avoid JS errors. (If charts rely on specific data,
        # they should be refactored later to also use the same filtered querysets.)
        rm_categories, rm_values = [], []
        branch_names, branch_values = [], []
        day_labels, day_values, month_labels, month_values = [], [], [], []

        return JsonResponse({
            "rm_categories": rm_categories,
            "rm_values": rm_values,
            "branch_names": branch_names,
            "branch_values": branch_values,
            "day_labels": day_labels,
            "day_values": day_values,
            "month_labels": month_labels,
            "month_values": month_values,

            # Card values (must match filtered dataset)
            "today_collection": today_collection,
            "yesterday_collection": yesterday_collection,
            "this_month_collection": this_month_collection,
            "last_month_collection": last_month_collection,

            "rm_link_collection": filtered_link_total,
            "gpay_collection": filtered_gpay_total,
            "filtered_total": filtered_total,
            "filtered_link_count": filtered_link_count,
            "filtered_gpay_count": filtered_gpay_count,
            "filtered_total_count": filtered_total_count,

            # Table rows
            "donations": donations,
        })

    # Non-AJAX: render full page.



    

    today = timezone.localdate()
    selected_date = request.GET.get("selected_date", "").strip()
    print("Selected Date:", selected_date)

    selected_rm_code = request.GET.get("rm_code", "all")
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    yesterday = today - timedelta(days=1)

    start_today = _start_of_day(today)
    start_tomorrow = _start_of_day(today + timedelta(days=1))

    start_yesterday = _start_of_day(yesterday)

    start_this_month = _start_of_month(today)
    start_next_month = _start_of_day(
        _add_months(today, 1).replace(day=1)
    )

    start_last_month = _start_of_month(
        _add_months(today.replace(day=1), -1)
    )
    

    # ---------------- Today ----------------

    today_link = (
        RMPayment.objects.filter(
            submitted_at__gte=start_today,
            submitted_at__lt=start_tomorrow,
        ).aggregate(total=Sum("donor_amount"))["total"]
        or 0
    )

    today_gpay = (
        RMGPayPayment.objects.filter(
            payment_date__gte=start_today,
            payment_date__lt=start_tomorrow,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    today_collection = today_link + today_gpay


    # ---------------- Yesterday ----------------

    yesterday_link = (
        RMPayment.objects.filter(
            submitted_at__gte=start_yesterday,
            submitted_at__lt=start_today,
        ).aggregate(total=Sum("donor_amount"))["total"]
        or 0
    )

    yesterday_gpay = (
        RMGPayPayment.objects.filter(
            payment_date__gte=start_yesterday,
            payment_date__lt=start_today,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    yesterday_collection = yesterday_link + yesterday_gpay


    # ---------------- This Month ----------------

    this_month_link = (
        RMPayment.objects.filter(
            submitted_at__gte=start_this_month,
            submitted_at__lt=start_next_month,
        ).aggregate(total=Sum("donor_amount"))["total"]
        or 0
    )

    this_month_gpay = (
        RMGPayPayment.objects.filter(
            payment_date__gte=start_this_month,
            payment_date__lt=start_next_month,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    this_month_collection = this_month_link + this_month_gpay


    # ---------------- Last Month ----------------

    last_month_link = (
        RMPayment.objects.filter(
            submitted_at__gte=start_last_month,
            submitted_at__lt=start_this_month,
        ).aggregate(total=Sum("donor_amount"))["total"]
        or 0
    )

    last_month_gpay = (
        RMGPayPayment.objects.filter(
            payment_date__gte=start_last_month,
            payment_date__lt=start_this_month,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    last_month_collection = last_month_link + last_month_gpay


    # ---------------- Total ----------------

    rm_link_collection = (
        RMPayment.objects.aggregate(
            total=Sum("donor_amount")
        )["total"]
        or 0
    )

    gpay_collection = (
        RMGPayPayment.objects.aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )


    rm_list = RM.objects.all()

    link_qs = RMPayment.objects.all()
    gpay_qs = RMGPayPayment.objects.all()
    
    # RM Filter
    if selected_rm_code and selected_rm_code != "all":
        link_qs = link_qs.filter(rm_code=selected_rm_code)
        gpay_qs = gpay_qs.filter(rm_code=selected_rm_code)
    
    # Date Filter
    if date_from:
        start_date = _start_of_day(
            datetime.strptime(date_from, "%Y-%m-%d").date()
        )
    
        link_qs = link_qs.filter(
            submitted_at__gte=start_date
        )
    
        gpay_qs = gpay_qs.filter(
            payment_date__gte=start_date
        )
    
    if date_to:
        end_date = _start_of_day(
            datetime.strptime(date_to, "%Y-%m-%d").date() + timedelta(days=1)
        )
    
        link_qs = link_qs.filter(
            submitted_at__lt=end_date
        )
    
        gpay_qs = gpay_qs.filter(
            payment_date__lt=end_date
        )

    filtered_link_total = (
        link_qs.aggregate(total=Sum("donor_amount"))["total"] or 0
    )

    filtered_gpay_total = (
        gpay_qs.aggregate(total=Sum("amount"))["total"] or 0
    )

    filtered_total = filtered_link_total + filtered_gpay_total

    filtered_link_count = link_qs.count()

    filtered_gpay_count = gpay_qs.count()

    filtered_total_count = filtered_link_count + filtered_gpay_count



    # ---------------- Day Donation (Last 7 days) - Branch-wise ----------------
    # Branch is identified by RM.rm_branch (values like: madurai, chennai, bangalore)
    last_7_start_date = today - timedelta(days=6)

    # Chronological labels (oldest -> newest)
    day_labels = [
        (last_7_start_date + timedelta(days=i)).strftime("%a")
        for i in range(7)
    ]

    # Prepare branch-wise maps: branch_key -> list[7] aligned to day_labels
    preferred_order = ["chennai", "madurai", "bangalore"]
    branch_keys = [*preferred_order]

    # Fetch all RM mappings for rm_code -> rm_branch
    rm_by_code = {rm.rm_code: rm for rm in RM.objects.all()}

    branch_totals_by_day = {
        bk: [0.0] * 7
        for bk in branch_keys
    }

    def _day_index(d):
        # d is a date object
        return (d - last_7_start_date).days

    # Use timezone-aware day boundaries (consistent with the summary-card
    # queries) so the filter returns rows correctly under USE_TZ=True.
    start_last7 = _start_of_day(last_7_start_date)
    end_last7 = _start_of_day(today + timedelta(days=1))

    # RMPayment (Link)
    rm_payments_qs = RMPayment.objects.filter(
        submitted_at__gte=start_last7,
        submitted_at__lt=end_last7,
    ).only("submitted_at", "donor_amount", "rm_code")

    for payment in rm_payments_qs:
        if not payment.submitted_at:
            continue
        idx = _day_index(payment.submitted_at.date())
        if idx < 0 or idx > 6:
            continue
        rm = rm_by_code.get(payment.rm_code)
        if not rm:
            continue
        branch_key = (rm.rm_branch or "").strip().lower() or "-"
        if branch_key not in branch_totals_by_day:
            continue
        branch_totals_by_day[branch_key][idx] += float(payment.donor_amount or 0)

    # RMGPayPayment (GPay) - combined exactly like summary cards
    gpay_qs = RMGPayPayment.objects.filter(
        payment_date__gte=start_last7,
        payment_date__lt=end_last7,
    )


    for payment in gpay_qs:
        if not payment.payment_date:
            continue
        idx = _day_index(payment.payment_date.date())
        if idx < 0 or idx > 6:
            continue
        rm = rm_by_code.get(payment.rm_code)
        if not rm:
            continue
        branch_key = (rm.rm_branch or "").strip().lower() or "-"
        if branch_key not in branch_totals_by_day:
            continue
        branch_totals_by_day[branch_key][idx] += float(payment.amount or 0)

    chennai_day_values = branch_totals_by_day.get("chennai", [0.0]*7)
    madurai_day_values = branch_totals_by_day.get("madurai", [0.0]*7)
    bangalore_day_values = branch_totals_by_day.get("bangalore", [0.0]*7)

    # ---------------- Day Donation Chart (Last 7 days, including today) ----------------
    last_7_dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]

    day_totals = {d: 0.0 for d in last_7_dates}

    for payment in RMPayment.objects.filter(
        submitted_at__gte=start_last7,
        submitted_at__lt=end_last7,
    ).only("submitted_at", "donor_amount"):
        if payment.submitted_at:
            d = payment.submitted_at.date()
            if d in day_totals:
                day_totals[d] += float(payment.donor_amount or 0)

    for payment in RMGPayPayment.objects.filter(
        payment_date__gte=start_last7,
        payment_date__lt=end_last7,
    ).only("payment_date", "amount"):
        if payment.payment_date:
            d = payment.payment_date.date()
            if d in day_totals:
                day_totals[d] += float(payment.amount or 0)

    day_categories = [
        d.strftime("%d %b") for d in last_7_dates
    ]

    day_values = [
        day_totals[d] for d in last_7_dates
    ]

    day_categories_json = json.dumps(day_categories)
    day_values_json = json.dumps(day_values)

    print(day_categories)
    print(day_values)




    # ---------------- Month Donation chart (12 months) - Branch-wise ----------------
    # Requirement: 3 series only: Chennai, Madurai, Bangalore
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Initialize branch -> 12 months totals (must be exactly 12 values each)
    chennai_month_values = [0.0] * 12
    madurai_month_values = [0.0] * 12
    bangalore_month_values = [0.0] * 12

    # Current year only
    today_year = timezone.localdate().year

    # Fetch rm_code -> rm_branch mapping (NO rm_name usage)
    rm_by_code = {rm.rm_code: rm for rm in RM.objects.all()}

    # Helper to convert month number to index (1-12 -> 0-11)
    def _month_index(dt):
        return int(dt.month) - 1

    # RMPayment: submitted_at (current year)
    for payment in RMPayment.objects.filter(
        submitted_at__year=today_year
    ).only("submitted_at", "donor_amount", "rm_code"):
        if not payment.submitted_at:
            continue
        idx = _month_index(payment.submitted_at)
        if idx < 0 or idx > 11:
            continue

        rm = rm_by_code.get(payment.rm_code)
        if not rm:
            continue

        branch_key = (rm.rm_branch or "").strip().lower()
        amt = float(payment.donor_amount or 0)

        if branch_key == "chennai":
            chennai_month_values[idx] += amt
        elif branch_key == "madurai":
            madurai_month_values[idx] += amt
        elif branch_key == "bangalore":
            bangalore_month_values[idx] += amt

    # RMGPayPayment: payment_date (current year)
    for payment in RMGPayPayment.objects.filter(
        payment_date__year=today_year
    ).only("payment_date", "amount", "rm_code"):
        if not payment.payment_date:
            continue
        idx = _month_index(payment.payment_date)
        if idx < 0 or idx > 11:
            continue

        rm = rm_by_code.get(payment.rm_code)
        if not rm:
            continue

        branch_key = (rm.rm_branch or "").strip().lower()
        amt = float(payment.amount or 0)

        if branch_key == "chennai":
            chennai_month_values[idx] += amt
        elif branch_key == "madurai":
            madurai_month_values[idx] += amt
        elif branch_key == "bangalore":
            bangalore_month_values[idx] += amt

    month_labels = month_labels
    month_categories = month_labels
    month_values = [
        chennai_month_values[i] + madurai_month_values[i] + bangalore_month_values[i]
        for i in range(12)
    ]


    rm_link_filter = {}
    rm_gpay_filter = {}

    if selected_date:


        if " to " in selected_date:


            start_str, end_str = selected_date.split(" to ")


            start_date = datetime.strptime(
                start_str.strip(),
                "%d %b, %Y"
            ).date()


            end_date = datetime.strptime(
                end_str.strip(),
                "%d %b, %Y"
            ).date()


            start_dt = _start_of_day(start_date)
            end_dt = _start_of_day(end_date + timedelta(days=1))

            rm_link_filter = {
                "submitted_at__gte": start_dt,
                "submitted_at__lt": end_dt,
            }


            rm_gpay_filter = {
                "payment_date__gte": start_dt,
                "payment_date__lt": end_dt,
            }

        else:


            selected = datetime.strptime(
                selected_date,
                "%d %b, %Y"
            ).date()


            start_dt = _start_of_day(selected)
            end_dt = _start_of_day(selected + timedelta(days=1))

            rm_link_filter = {
                "submitted_at__gte": start_dt,
                "submitted_at__lt": end_dt,
            }


            rm_gpay_filter = {
                "payment_date__gte": start_dt,
                "payment_date__lt": end_dt,
            }

    else:


        rm_link_filter = {
            "submitted_at__gte": start_this_month,
            "submitted_at__lt": start_next_month,
        }


        rm_gpay_filter = {
            "payment_date__gte": start_this_month,
            "payment_date__lt": start_next_month,
        }

    rm_chart = defaultdict(float)

    for payment in RMPayment.objects.filter(**rm_link_filter):
        key = f"{payment.rm_name} "
        rm_chart[key] += float(payment.donor_amount or 0)

    for payment in RMGPayPayment.objects.filter(**rm_gpay_filter):
        key = f"{payment.rm_name} "
        rm_chart[key] += float(payment.amount or 0)
        
    rm_chart = dict(
        sorted(
            rm_chart.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    )

    rm_categories = list(rm_chart.keys())
    rm_values = list(rm_chart.values())

    branch_totals = defaultdict(float)

    rm_by_code = {rm.rm_code: rm for rm in RM.objects.all()}

    # Link (RMPayment)
    for payment in RMPayment.objects.filter(**rm_link_filter):
        
        rm = rm_by_code.get(payment.rm_code)
        if not rm:
            continue
        branch_key = (rm.rm_branch or "").strip().lower()
        if not branch_key:
            branch_key = "-"
        branch_totals[branch_key] += float(payment.donor_amount or 0)

    # GPay (RMGPayPayment)
    for payment in RMGPayPayment.objects.filter(**rm_gpay_filter):

        rm = rm_by_code.get(payment.rm_code)
        if not rm:
            continue
        branch_key = (rm.rm_branch or "").strip().lower()
        if not branch_key:
            branch_key = "-"
        branch_totals[branch_key] += float(payment.amount or 0)

    # Stable ordering: madurai, chennai, bangalore, then others
    preferred_order = ["chennai", "madurai", "bangalore"]
    other_keys = [k for k in branch_totals.keys() if k not in preferred_order]
    other_keys.sort()
    ordered_branch_keys = [k for k in preferred_order if k in branch_totals] + other_keys

    # Labels for chart
    branch_names = [k.capitalize() if k != "-" else "-" for k in ordered_branch_keys]
    branch_values = [branch_totals[k] for k in ordered_branch_keys]

    # Color mapping (match style used elsewhere; provide fallback list)
    branch_color_map = {
        "madurai": "#1abc9c",   # teal
        "chennai": "#3498db",   # blue
        "bangalore": "#9b59b6", # purple
        "-": "#95a5a6",         # gray
    }

    branch_colors = [branch_color_map.get(k, "#5ec2dd") for k in ordered_branch_keys]

    branch_names_json = json.dumps(branch_names)
    branch_values_json = json.dumps(branch_values)
    branch_colors_json = json.dumps(branch_colors)

    print(month_labels)
    print(chennai_month_values)
    print(madurai_month_values)
    print(bangalore_month_values)



    
    # Default table queryset (Today only)
    table_link_qs = link_qs
    table_gpay_qs = gpay_qs

    # If no date filter is selected, show only today's records in table
    if not date_from and not date_to:
        table_link_qs = table_link_qs.filter(
            submitted_at__gte=start_today,
            submitted_at__lt=start_tomorrow,
        )

        table_gpay_qs = table_gpay_qs.filter(
            payment_date__gte=start_today,
            payment_date__lt=start_tomorrow,
        )


    donations = []

    # Link donations (RMPayment)
    for payment in table_link_qs.order_by("-submitted_at"):
        donations.append(
            {
                "date": payment.submitted_at.strftime("%d-%m-%Y")
                    if payment.submitted_at else "-",
                "virtual_label": f"{payment.rm_name} - {payment.rm_code}",
                "source": "Link",
                "amount": payment.donor_amount,
                "submitted_at": timezone.localtime(payment.submitted_at).strftime("%d-%m-%Y %I:%M %p")
                    if payment.submitted_at else "-",
                "status": payment.easebuzz_payment_status or "unsettled",
                "mode": payment.easebuzz_payment_mode or payment.payment_mode or "-",
                "ptid": payment.easebuzz_transaction_id or payment.txnid or "-",
                "donor_name": payment.donor_name,
                "donor_mobile": payment.donor_mobile,
                "donor_email": payment.donor_email,
                "donor_address": payment.donor_address,
                "uqid": payment.txnid or "-",
                "receipt_no": payment.receipt_no,
            }
        )

    # GPay donations (RMGPayPayment)
    for payment in table_gpay_qs.order_by("-payment_date"):
        donations.append(
            {
                "date": payment.payment_date.strftime("%d-%m-%Y")
                    if payment.payment_date else "-",
                "virtual_label": f"{payment.rm_name} - {payment.rm_code}",
                "source": "GPay",
                "amount": payment.amount,
                "submitted_at": timezone.localtime(payment.payment_date).strftime("%d-%m-%Y %I:%M %p")
                    if payment.payment_date else "-",
                "status": "Success",
                "mode": "UPI",
                "ptid": payment.gpay_reference_id or "-",
                "donor_name": payment.donor_name,
                "donor_mobile": payment.donor_mobile,
                "donor_email": payment.donor_email,
                "donor_address": payment.donor_address,
                "uqid": payment.gpay_reference_id or "-",
                "receipt_no": payment.receipt_no,
            }
        )

    donations.sort(key=lambda d: d.get("submitted_at") or d.get("date"), reverse=True)
    print(donations[:3])
    return render(
        request,
        "dashboard/RM_Portal.html",
        {   
            
            "donations": donations,
            "rm_list": rm_list,
    
            "today_collection": today_collection,
            "yesterday_collection": yesterday_collection,
            "this_month_collection": this_month_collection,
            "last_month_collection": last_month_collection,
    
            "rm_link_collection": rm_link_collection,
            "gpay_collection": gpay_collection,
    
            # Day Donation chart data (branch-wise, last 7 days)
            "day_labels": day_labels,
            "chennai_day": chennai_day_values,
            "madurai_day": madurai_day_values,
            "bangalore_day": bangalore_day_values,
    
            # Existing combined day chart data (kept for existing JS)
            "day_categories_json": json.dumps(day_categories),
            "day_values_json": json.dumps(day_values),
    
            # Month Donation chart data (branch-wise, 12 months)
            "month_labels": month_labels,
            "chennai_month": chennai_month_values,
            "madurai_month": madurai_month_values,
            "bangalore_month": bangalore_month_values,
    
            # Backward compatibility for any existing combined month chart usage
            "month_categories_json": json.dumps(month_categories),
            "month_values_json": json.dumps(month_values),
    
    
            "rm_categories": rm_categories,
            "rm_values": rm_values,

            "branch_names": branch_names,
            "branch_values": branch_values,
            "branch_names_json": branch_names_json,
            "branch_values_json": branch_values_json,
            "branch_colors_json": branch_colors_json,

            "filtered_link_total": filtered_link_total,
            "filtered_gpay_total": filtered_gpay_total,
            "filtered_total": filtered_total,
            
            "filtered_link_count": filtered_link_count,
            "filtered_gpay_count": filtered_gpay_count,
            "filtered_total_count": filtered_total_count,
        },
    )
    