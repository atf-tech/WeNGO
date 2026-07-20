from __future__ import annotations
from datetime import date, datetime, timedelta
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from dashboard.models import RM
from easypay.models import RMPayment, RMGPayPayment
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

 


    def _row_from_link(p: RMPayment):
        return {
            "date": timezone.localtime(p.submitted_at).strftime("%d %b, %Y"),
            "donor_name": p.donor_name or "-",
            "mobile": p.donor_mobile or "-",
            "email": p.donor_email or "-",
            "address": p.donor_address or "-",
            "receipt_no": p.receipt_no or "-",
            "payment_mode": p.easebuzz_payment_mode or p.payment_mode or "-",
            "status": p.easebuzz_payment_status or p.payment_status or "-",
            "source": "Link",
        }

    def _row_from_gpay(p: RMGPayPayment):
        return {
            "date": timezone.localtime(p.payment_date).strftime("%d %b, %Y"),
            "donor_name": p.donor_name or "-",
            "mobile": p.donor_mobile or "-",
            "email": p.donor_email or "-",
            "address": p.donor_address or "-",
            "receipt_no": p.receipt_no or "-",
            "payment_mode": "GPay",
            "status": "Success",
            "source": "GPay",
        }



    link_rows = list(
        RMPayment.objects.filter(rm_code=rm.rm_code, is_paid=True)
        .order_by("-submitted_at")[:30]
        .select_related()
    )
    gpay_rows = list(
        RMGPayPayment.objects.filter(rm_code=rm.rm_code)
        .order_by("-payment_date")[:30]
        .select_related()
    )
 

    receipt_rows = [_row_from_link(p) for p in link_rows] + [_row_from_gpay(p) for p in gpay_rows] 

    # Sort by date parsed (best-effort)
    def _parse_for_sort(r):
        # already formatted as %d %b, %Y in the row
        try:
            return datetime.strptime(r["date"], "%d %b, %Y")
        except Exception:
            return datetime.min

    receipt_rows.sort(key=_parse_for_sort, reverse=True)
    receipt_rows = receipt_rows[:50]


    print("RM Code:", rm.rm_code)

    print("Link Today:", link_today_qs.count())
    print("GPay Today:", gpay_today_qs.count())

    payment_link = request.build_absolute_uri(f"/easepay/{rm.rm_code}/")

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
        
        "receipt_rows": receipt_rows,
        "today": today,
    }

    return render(request, "RMPortal/index.html", context)

