from django.shortcuts import render
from datetime import timedelta
import calendar
import json
from collections import defaultdict
from django.db.models import Sum
from django.utils import timezone
from dashboard.models import RM
from easypay.models import RMGPayPayment, RMPayment

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



def RM_Portal(request):
    """Render RM Portal table with only Link (RMPayment) + GPay (RMGPayPayment) donations."""

    today = timezone.localdate()
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

    # ---------------- Day Donation (Last 7 days) - Branch-wise ----------------
    # Branch is identified by RM.rm_branch (values like: madurai, chennai, bangalore)
    last_7_start_date = today - timedelta(days=6)

    # Chronological labels (oldest -> newest)
    day_labels = [
        (last_7_start_date + timedelta(days=i)).strftime("%a")
        for i in range(7)
    ]

    # Prepare branch-wise maps: branch_key -> list[7] aligned to day_labels
    preferred_order = ["madurai", "chennai", "bangalore"]
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

    rm_chart = defaultdict(float)

    for payment in RMPayment.objects.all():
        key = f"{payment.rm_name} ({payment.rm_code})"
        rm_chart[key] += float(payment.donor_amount or 0)

    for payment in RMGPayPayment.objects.all():
        key = f"{payment.rm_name} ({payment.rm_code})"
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
    for payment in RMPayment.objects.filter(
        submitted_at__gte=start_this_month,
        submitted_at__lt=start_next_month,
    ):
        rm = rm_by_code.get(payment.rm_code)
        if not rm:
            continue
        branch_key = (rm.rm_branch or "").strip().lower()
        if not branch_key:
            branch_key = "-"
        branch_totals[branch_key] += float(payment.donor_amount or 0)

    # GPay (RMGPayPayment)
    for payment in RMGPayPayment.objects.filter(
        payment_date__gte=start_this_month,
        payment_date__lt=start_next_month,
    ):
        rm = rm_by_code.get(payment.rm_code)
        if not rm:
            continue
        branch_key = (rm.rm_branch or "").strip().lower()
        if not branch_key:
            branch_key = "-"
        branch_totals[branch_key] += float(payment.amount or 0)

    # Stable ordering: madurai, chennai, bangalore, then others
    preferred_order = ["madurai", "chennai", "bangalore"]
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




    donations = []

    # Link donations (RMPayment)
    for payment in RMPayment.objects.all().order_by("-submitted_at"):
        donations.append(
            {
                "date": payment.submitted_at,
                "virtual_label": f"{payment.rm_name} - {payment.rm_code}",
                "source": "Link",
                "amount": payment.donor_amount,
                "submitted_at": payment.submitted_at,
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
    for payment in RMGPayPayment.objects.all().order_by("-payment_date"):
        donations.append(
            {
                "date": payment.payment_date,
                "virtual_label": f"{payment.rm_name} - {payment.rm_code}",
                "source": "GPay",
                "amount": payment.amount,
                "submitted_at": payment.payment_date,
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

    
            "rm_categories_json": json.dumps(rm_categories),
            "rm_values_json": json.dumps(rm_values),
        },
    )
