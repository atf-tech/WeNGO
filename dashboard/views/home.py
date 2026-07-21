from datetime import timedelta,datetime
import calendar
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from easypay.models import RMPayment, RMGPayPayment
from website.models import HomeDonation, ServiceDonation
from django.http import JsonResponse
from django.template.loader import render_to_string
from dashboard.views.auth import superuser_required


def _success_rmpayment_filter(qs):
    # Reuse existing model fields from easypay/models.py
    # RMPayment has `is_paid` and `payment_status`.
    return qs.filter(is_paid=True).exclude(payment_status__in=["failed", "Failure", "FAILED"])


def _success_rmgpay_filter(qs):
    # RMGPayPayment model doesn't expose an explicit `is_paid` in current model.
    # Treat it as successful/paid when it's present in the system.
    # If later a payment-status field exists, switch to that.
    return qs


def _start_of_day(d):
    return timezone.make_aware(
        timezone.datetime.combine(d, timezone.datetime.min.time()),
        timezone.get_current_timezone(),
    )


def _start_of_month(d):
    return _start_of_day(d.replace(day=1))


def _add_months(d, months: int):
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return d.replace(year=year, month=month, day=day)


def _window_bounds_for_date(selected_date):
    """Return aware datetime bounds for [selected_date, selected_date] inclusive."""
    start = _start_of_day(selected_date)
    end = timezone.make_aware(
        timezone.datetime.combine(selected_date, timezone.datetime.max.time()),
        timezone.get_current_timezone(),
    )
    return start, end


def _window_bounds_for_range(start_date, end_date):
    """Inclusive date range -> aware datetime start/end."""
    start = _start_of_day(start_date)
    end = timezone.make_aware(
        timezone.datetime.combine(end_date, timezone.datetime.max.time()),
        timezone.get_current_timezone(),
    )
    return start, end


def _sum_decimal(qs, field_name: str):
    return qs.aggregate(total=Sum(field_name))["total"] or 0


def _sum_home_total(qs):
    return _sum_decimal(qs, "total_price")


def _sum_service_total(qs):
    return _sum_decimal(qs, "donation_amount")


@superuser_required(login_url='/dashboard/login')
def home(request):

    # Parse selected_date from query (Flatpickr range returns e.g.:
    #  - "16 Jul, 2026"
    #  - "15 Jul, 2026 - 17 Jul, 2026")
    selected_date = request.GET.get("selected_date", "").strip()

    filter_start_date = None
    filter_end_date = None

    if selected_date:
        try:
            # Normalize dash separators
            parts = None
            if " to " in selected_date:
                parts = selected_date.split(" to ", 1)
            elif " - " in selected_date:
                parts = selected_date.split(" - ", 1)
            else:
                parts = [selected_date, selected_date]

            start_str = parts[0].strip()
            end_str = parts[1].strip()

            filter_start_date = datetime.strptime(start_str, "%d %b, %Y").date()
            filter_end_date = datetime.strptime(end_str, "%d %b, %Y").date()
        except Exception:
            # Fallback to today if parsing fails
            filter_start_date = None
            filter_end_date = None

    now_local = timezone.localtime(timezone.now())
    today = now_local.date()

    if filter_start_date is None or filter_end_date is None:
        filter_start_date = today
        filter_end_date = today

    today = now_local.date()
    yesterday = today - timedelta(days=1)

    # Cards time windows
    start_today, end_today = _window_bounds_for_date(today)
    start_yesterday, end_yesterday = _window_bounds_for_date(yesterday)

    start_this_month = _start_of_month(today)
    end_this_month = timezone.make_aware(
        timezone.datetime.combine(today.replace(day=1), timezone.datetime.min.time()),
        timezone.get_current_timezone(),
    )
    _, last_day_num = calendar.monthrange(today.year, today.month)
    end_this_month = timezone.make_aware(
        timezone.datetime.combine(today.replace(day=last_day_num), timezone.datetime.max.time()),
        timezone.get_current_timezone(),
    )

    prev_month_date = _add_months(today.replace(day=1), -1)
    start_last_month = _start_of_month(prev_month_date)
    _, prev_last_day = calendar.monthrange(prev_month_date.year, prev_month_date.month)
    end_last_month = timezone.make_aware(
        timezone.datetime.combine(prev_month_date.replace(day=prev_last_day), timezone.datetime.max.time()),
        timezone.get_current_timezone(),
    )

    # Base successful/paid querysets
    rm_link_base = _success_rmpayment_filter(RMPayment.objects.all())
    gpay_base = _success_rmgpay_filter(RMGPayPayment.objects.all())

    # RM + GPay windowed totals
    rm_today = _sum_decimal(
        rm_link_base.filter(submitted_at__range=(start_today, end_today)),
        "donor_amount",
    )
    gpay_today = _sum_decimal(
        gpay_base.filter(payment_date__range=(start_today, end_today)),
        "amount",
    )

    rm_yesterday = _sum_decimal(
        rm_link_base.filter(submitted_at__range=(start_yesterday, end_yesterday)),
        "donor_amount",
    )
    gpay_yesterday = _sum_decimal(
        gpay_base.filter(payment_date__range=(start_yesterday, end_yesterday)),
        "amount",
    )

    rm_this_month = _sum_decimal(
        rm_link_base.filter(submitted_at__range=(start_this_month, end_this_month)),
        "donor_amount",
    )
    gpay_this_month = _sum_decimal(
        gpay_base.filter(payment_date__range=(start_this_month, end_this_month)),
        "amount",
    )

    rm_last_month = _sum_decimal(
        rm_link_base.filter(submitted_at__range=(start_last_month, end_last_month)),
        "donor_amount",
    )
    gpay_last_month = _sum_decimal(
        gpay_base.filter(payment_date__range=(start_last_month, end_last_month)),
        "amount",
    )

    # Website donations totals (Home + Service)
    home_today = _sum_home_total(
        HomeDonation.objects.filter(is_paid=True, submitted_at__range=(start_today, end_today))
    )
    home_yesterday = _sum_home_total(
        HomeDonation.objects.filter(is_paid=True, submitted_at__range=(start_yesterday, end_yesterday))
    )
    home_this_month = _sum_home_total(
        HomeDonation.objects.filter(is_paid=True, submitted_at__range=(start_this_month, end_this_month))
    )
    home_last_month = _sum_home_total(
        HomeDonation.objects.filter(is_paid=True, submitted_at__range=(start_last_month, end_last_month))
    )

    service_today = _sum_service_total(
        ServiceDonation.objects.filter(is_paid=True, created_at__range=(start_today, end_today))
    )
    service_yesterday = _sum_service_total(
        ServiceDonation.objects.filter(is_paid=True, created_at__range=(start_yesterday, end_yesterday))
    )
    service_this_month = _sum_service_total(
        ServiceDonation.objects.filter(is_paid=True, created_at__range=(start_this_month, end_this_month))
    )
    service_last_month = _sum_service_total(
        ServiceDonation.objects.filter(is_paid=True, created_at__range=(start_last_month, end_last_month))
    )

    # Overall cards
    today_overall = rm_today + gpay_today + home_today + service_today
    yesterday_overall = rm_yesterday + gpay_yesterday + home_yesterday + service_yesterday
    this_month_overall = rm_this_month + gpay_this_month + home_this_month + service_this_month
    last_month_overall = rm_last_month + gpay_last_month + home_last_month + service_last_month

    # RM card values (RM related only)
    rm_collection_today = rm_today + gpay_today

    # Website card value (Website related only)
    website_collection_today = home_today + service_today

    # Active RM (Today) = unique RM collected today via link+gpay
    active_rm_codes = set(
        rm_link_base.filter(submitted_at__range=(start_today, end_today)).values_list("rm_code", flat=True)
    ) | set(
        gpay_base.filter(payment_date__range=(start_today, end_today)).values_list("rm_code", flat=True)
    )
    active_rm_today_count = len([c for c in active_rm_codes if c])

    # Charts
    # Last 7 days: per day overall = RM+GPay+Home+Service
    last_7_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    last7_day_totals = {d: 0.0 for d in last_7_dates}

    # RM
    for p in rm_link_base.filter(submitted_at__date__gte=last_7_dates[0], submitted_at__date__lte=last_7_dates[-1]).only(
        "submitted_at", "donor_amount"
    ):
        d = timezone.localtime(p.submitted_at).date() if p.submitted_at else None
        if d in last7_day_totals:
            last7_day_totals[d] += float(p.donor_amount or 0)

    # GPay
    for p in gpay_base.filter(payment_date__date__gte=last_7_dates[0], payment_date__date__lte=last_7_dates[-1]).only(
        "payment_date", "amount"
    ):
        d = timezone.localtime(p.payment_date).date() if p.payment_date else None
        if d in last7_day_totals:
            last7_day_totals[d] += float(p.amount or 0)

    # Home
    for p in HomeDonation.objects.filter(is_paid=True, submitted_at__gte=_start_of_day(last_7_dates[0]), submitted_at__lt=_start_of_day(last_7_dates[-1] + timedelta(days=1))).only(
        "submitted_at", "total_price"
    ):

        d = timezone.localtime(p.submitted_at).date() if p.submitted_at else None
        if d in last7_day_totals:
            last7_day_totals[d] += float(p.total_price or 0)

    # Service
    for p in ServiceDonation.objects.filter(is_paid=True, created_at__date__gte=last_7_dates[0], created_at__date__lte=last_7_dates[-1]).only(
        "created_at", "donation_amount"
    ):
        d = timezone.localtime(p.created_at).date() if p.created_at else None
        if d in last7_day_totals:
            last7_day_totals[d] += float(p.donation_amount or 0)

    # =========================================
    # Gradient Chart - Today 24 Hours
    # =========================================

    gradient_categories = []
    gradient_values = []

    today_start = _start_of_day(today)

    for hour in range(24):

        hour_start = today_start + timedelta(hours=hour)
        hour_end = hour_start + timedelta(hours=1)

        total = 0

        # RM Donation
        total += float(
            _sum_decimal(
                rm_link_base.filter(
                    submitted_at__gte=hour_start,
                    submitted_at__lt=hour_end,
                ),
                "donor_amount",
            )
        )

        # GPay Donation
        total += float(
            _sum_decimal(
                gpay_base.filter(
                    payment_date__gte=hour_start,
                    payment_date__lt=hour_end,
                ),
                "amount",
            )
        )

        # Home Donation
        total += float(
            _sum_home_total(
                HomeDonation.objects.filter(
                    is_paid=True,
                    submitted_at__gte=hour_start,
                    submitted_at__lt=hour_end,
                )
            )
        )

        # Service Donation
        total += float(
            _sum_service_total(
                ServiceDonation.objects.filter(
                    is_paid=True,
                    created_at__gte=hour_start,
                    created_at__lt=hour_end,
                )
            )
        )

        gradient_categories.append(hour_start.strftime("%I %p"))
        gradient_values.append(total)


    weekday_idx = today.weekday()  # Monday=0
    week_start = today - timedelta(days=weekday_idx)
    week_end = week_start + timedelta(days=6)

    week_categories = []
    week_values = []

    current = week_start

    while current <= week_end:

        start = _start_of_day(current)
        end = start + timedelta(days=1)

        total = 0

        total += float(
            _sum_decimal(
                rm_link_base.filter(
                    submitted_at__gte=start,
                    submitted_at__lt=end
                ),
                "donor_amount"
            )
        )

        total += float(
            _sum_decimal(
                gpay_base.filter(
                    payment_date__gte=start,
                    payment_date__lt=end
                ),
                "amount"
            )
        )

        total += float(
            _sum_home_total(
                HomeDonation.objects.filter(
                    is_paid=True,
                    submitted_at__gte=start,
                    submitted_at__lt=end
                )
            )
        )

        total += float(
            _sum_service_total(
                ServiceDonation.objects.filter(
                    is_paid=True,
                    created_at__gte=start,
                    created_at__lt=end
                )
            )
        )

        week_categories.append(current.strftime("%A"))
        week_values.append(total)

        current += timedelta(days=1)

    # This month chart = daily totals for current month (RM+GPay+Home+Service)
    # ==========================================
    # This Month Weekly Chart
    # ==========================================
    
    first_day = today.replace(day=1)
    _, last_day = calendar.monthrange(today.year, today.month)
    
    month_categories = []
    month_values = []
    
    for week in range(5):
    
        week_start_day = week * 7 + 1
    
        if week_start_day > last_day:
            break
        
        week_end_day = min(week_start_day + 6, last_day)
    
        start_date = today.replace(day=week_start_day)
        end_date = today.replace(day=week_end_day)
    
        start = _start_of_day(start_date)
        end = _start_of_day(end_date + timedelta(days=1))
    
        total = 0
    
        # RM Link
        total += float(
            _sum_decimal(
                rm_link_base.filter(
                    submitted_at__gte=start,
                    submitted_at__lt=end,
                ),
                "donor_amount",
            )
        )
    
        # GPay
        total += float(
            _sum_decimal(
                gpay_base.filter(
                    payment_date__gte=start,
                    payment_date__lt=end,
                ),
                "amount",
            )
        )
    
        # Home
        total += float(
            _sum_home_total(
                HomeDonation.objects.filter(
                    is_paid=True,
                    submitted_at__gte=start,
                    submitted_at__lt=end,
                )
            )
        )
    
        # Service
        total += float(
            _sum_service_total(
                ServiceDonation.objects.filter(
                    is_paid=True,
                    created_at__gte=start,
                    created_at__lt=end,
                )
            )
        )
    
        month_categories.append(f"Week {week + 1}")
        month_values.append(total)

    # (selected_date parsing handled above for AJAX + non-AJAX)


    start_dt = _start_of_day(filter_start_date)
    end_dt = _start_of_day(filter_end_date + timedelta(days=1))

    combined_qs = []

    # ---------------- RM ----------------

    for rp in _success_rmpayment_filter(
        RMPayment.objects.filter(
            submitted_at__gte=start_dt,
            submitted_at__lt=end_dt,
        )
    ):

        combined_qs.append({
            "receipt_no": rp.receipt_no,
            "date": rp.submitted_at,
            "source": "RM",
            "donor_name": rp.donor_name,
            "donor_mobile": rp.donor_mobile,
            "donor_email": rp.donor_email,
            "amount": rp.donor_amount,
            "payment_status": rp.easebuzz_payment_status,
            "payment_mode": rp.easebuzz_payment_mode,
            "payment_transaction_id": rp.easebuzz_transaction_id,
            "transaction_id": rp.txnid,
        })

    # ---------------- GPay ----------------

    for gp in gpay_base.filter(
        payment_date__gte=start_dt,
        payment_date__lt=end_dt,
    ):

        combined_qs.append({
            "receipt_no": gp.receipt_no,
            "date": gp.payment_date,
            "source": "GPay",
            "donor_name": gp.donor_name,
            "donor_mobile": gp.donor_mobile,
            "donor_email": gp.donor_email,
            "amount": gp.amount,
            "payment_status": "Paid",
            "payment_mode": "GPay",
            "payment_transaction_id": gp.gpay_reference_id,
            "transaction_id": gp.gpay_reference_id,
        })

    # ---------------- Home ----------------

    for hd in HomeDonation.objects.filter(
        is_paid=True,
        submitted_at__gte=start_dt,
        submitted_at__lt=end_dt,
    ):

        combined_qs.append({
            "receipt_no": hd.receipt_no,
            "date": hd.submitted_at,
            "source": "Home",
            "donor_name": hd.donor_name,
            "donor_mobile": hd.donor_mobile,
            "donor_email": hd.donor_email,
            "amount": hd.total_price,
            "payment_status": hd.easebuzz_payment_status,
            "payment_mode": hd.easebuzz_payment_mode,
            "payment_transaction_id": hd.easebuzz_transaction_id,
            "transaction_id": hd.txnid,
        })

    # ---------------- Service ----------------

    for sd in ServiceDonation.objects.filter(
        is_paid=True,
        created_at__gte=start_dt,
        created_at__lt=end_dt,
    ):

        combined_qs.append({
            "receipt_no": sd.receipt_no,
            "date": sd.created_at,
            "source": "Service",
            "donor_name": sd.donor_name,
            "donor_mobile": sd.donor_mobile,
            "donor_email": sd.donor_email,
            "amount": sd.donation_amount,
            "payment_status": sd.easebuzz_payment_status,
            "payment_mode": sd.easebuzz_payment_mode,
            "payment_transaction_id": sd.easebuzz_transaction_id,
            "transaction_id": sd.txnid,
        })

    combined_qs.sort( key=lambda x: x["date"], reverse=True )
    print("Filtered Records:", len(combined_qs))
    print("Start:", start_dt)
    print("End:", end_dt)


    context = {
        "today_overall": today_overall,
        "yesterday_overall": yesterday_overall,
        "this_month_overall": this_month_overall,
        "last_month_overall": last_month_overall,
        "rm_collection_today": rm_collection_today,
        "website_collection_today": website_collection_today,
        "active_rm_today_count": active_rm_today_count,
        # charts
        "gradient_categories": gradient_categories,
        "gradient_values": gradient_values,
        "pie_labels": week_categories,
        "pie_values": week_values,
        "month_categories": month_categories,
        "month_values": month_values,
        # recent
        "recent_success_donations": combined_qs,

        "selected_date_str": selected_date,
        "filter_start_date": filter_start_date,
        "filter_end_date": filter_end_date,
    }   

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        tbody_html = render_to_string(
            "dashboard/partials/donation_table_rows.html",
            context,
            request=request,
        )

        return JsonResponse({
            "tbody": tbody_html,
        })

    return render(request, "dashboard/home.html", context)

