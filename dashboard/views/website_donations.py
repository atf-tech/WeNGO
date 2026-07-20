import calendar
import logging

from django.shortcuts import render
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, timedelta, time
import json
from website.models import HomeDonation, ServiceDonation
from django.db.models.functions import ExtractHour

logger = logging.getLogger(__name__)


def _verified_total(queryset, amount_field):
    """Return the Sum() of `amount_field`, verified against the actual
    database records that the queryset selects before aggregating."""
    matching = list(queryset.values_list("pk", amount_field))
    python_total = sum((value or 0) for _, value in matching)

    # Extra safety: ensure we don't have duplicates in the queryset results.
    # (Joins/annotations can cause duplicate rows.)
    unique_pks = {pk for pk, _ in matching}
    if len(unique_pks) != len(matching):
        logger.warning(
            "Duplicate rows detected for %s (%s): rows=%s unique_pks=%s",
            queryset.model.__name__,
            amount_field,
            len(matching),
            len(unique_pks),
        )

    agg_total = queryset.aggregate(total=Sum(amount_field))["total"] or 0

    if python_total != agg_total:
        logger.warning(
            "Donation total mismatch for %s.%s: aggregate=%s, record_sum=%s, "
            "records=%s",
            queryset.model.__name__,
            amount_field,
            agg_total,
            python_total,
            len(matching),
        )

    return agg_total


def Website_Donations(request):

    now_local = timezone.localtime(timezone.now())
    today_local = now_local.date()

    # Default = Today
    selected_date_str = request.GET.get("selected_date")

    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str,"%Y-%m-%d").date()
    else:
        selected_date = today_local

    yesterday = selected_date - timedelta(days=1)

    ## --- Selected Date ---
    start_today = timezone.make_aware(
        datetime.combine(selected_date, time.min)
    )

    end_today = timezone.make_aware(
        datetime.combine(selected_date, time.max)
    )

    # --- Yesterday ---
    start_yesterday = timezone.make_aware(
        datetime.combine(yesterday, time.min)
    )

    end_yesterday = timezone.make_aware(
        datetime.combine(yesterday, time.max)
    )

    # --- Current month  ---
    start_this_month = timezone.make_aware(
        datetime.combine(
            selected_date.replace(day=1),
            time.min,
        )
    )

    

    end_this_month = timezone.make_aware(
        datetime.combine(
            selected_date,
            time.max,
        )
    )

    # --- Previous month---

    first_day_current_month = selected_date.replace(day=1)
    last_day_prev_month = first_day_current_month - timedelta(days=1)

    start_last_month = timezone.make_aware(
        datetime.combine(
            last_day_prev_month.replace(day=1),
            time.min,
        )
    )
    end_last_month = timezone.make_aware(
        datetime.combine(
            last_day_prev_month,
            time.max,
        )
    )


    # =====================================
    # HOME DONATIONS (submitted_at, independent of Service)
    # =====================================

    home_today_qs = HomeDonation.objects.filter(
        is_paid=True,
        submitted_at__range=(start_today, end_today),
    )
    home_yesterday_qs = HomeDonation.objects.filter(
        is_paid=True,
        submitted_at__range=(start_yesterday, end_yesterday),
    )
    home_yesterday = _verified_total(
        home_yesterday_qs,
        "total_price",
    )
    home_this_month_qs = HomeDonation.objects.filter(
        is_paid=True,
        submitted_at__range=(start_this_month, end_this_month),
    )
    home_last_month_qs = HomeDonation.objects.filter(
        is_paid=True,
        submitted_at__range=(start_last_month, end_last_month),
    )

    home_today = _verified_total(home_today_qs, "total_price")
    home_yesterday = _verified_total(home_yesterday_qs,"total_price",)
    home_this_month = _verified_total(home_this_month_qs, "total_price")
    home_last_month = _verified_total(home_last_month_qs, "total_price")

    # =====================================
    # SERVICE DONATIONS (created_at, independent of Home)
    # =====================================

    service_today_qs = ServiceDonation.objects.filter(
        is_paid=True,
        created_at__range=(start_today, end_today),
    )
    service_yesterday_qs = ServiceDonation.objects.filter(
        is_paid=True,
        created_at__range=(start_yesterday, end_yesterday),
    )
    service_yesterday = _verified_total(
        service_yesterday_qs,
        "donation_amount",
    )
    service_this_month_qs = ServiceDonation.objects.filter(
        is_paid=True,
        created_at__range=(start_this_month, end_this_month),
    )
    service_last_month_qs = ServiceDonation.objects.filter(
        is_paid=True,
        created_at__range=(start_last_month, end_last_month),
    )

    service_today = _verified_total(service_today_qs, "donation_amount")
    service_yesterday = _verified_total(
        service_yesterday_qs,
        "donation_amount",
    )
    service_this_month = _verified_total(
        service_this_month_qs,
        "donation_amount",
    )
    service_last_month = _verified_total(
        service_last_month_qs,
        "donation_amount",
    )


    # =====================================
    # TABLE DATA
    # =====================================

    home_donations = (
        HomeDonation.objects
        .filter(
            is_paid=True,
            submitted_at__range=(start_today, end_today),
        )
        .order_by("-submitted_at")
    )

    service_donations = (
        ServiceDonation.objects
        .filter(
            is_paid=True,
            created_at__range=(start_today, end_today),
        )
        .select_related("service")
        .order_by("-created_at")
    )



    # =====================================
    # TODAY HOURLY CHART DATA
    # =====================================

    

    # =====================================
    # TODAY HOURLY CHART DATA
    # =====================================

    home_chart = {i: 0 for i in range(24)}
    service_chart = {i: 0 for i in range(24)}

    # Home Donations
    for obj in home_today_qs:
        hour = timezone.localtime(obj.submitted_at).hour
        home_chart[hour] += float(obj.total_price)

    # Service Donations
    for obj in service_today_qs:
        print(
            obj.created_at,
            timezone.localtime(obj.created_at),
            timezone.localtime(obj.created_at).hour,
            obj.donation_amount,
        )
        print(service_chart)
        hour = timezone.localtime(obj.created_at).hour
        service_chart[hour] += float(obj.donation_amount)

    home_chart_data = []
    service_chart_data = []

    for hour in range(24):

        ampm = "PM" if hour >= 12 else "AM"
        display_hour = hour % 12 or 12
        label = f"{display_hour:02d} {ampm}"

        home_chart_data.append({
            "x": label,
            "y": home_chart[hour],
        })

        service_chart_data.append({
            "x": label,
            "y": service_chart[hour],
        })

    print(home_chart_data)
    print(service_chart_data)
    print(home_today_qs.values("submitted_at", "total_price"))
    print(service_today_qs.values("created_at", "donation_amount"))
    

    # =====================================
    # CONTEXT
    # =====================================

    context = {
        "home_today": home_today,
        "home_yesterday": home_yesterday,
        "home_this_month": home_this_month,
        "home_last_month": home_last_month,

        "service_today": service_today,
        "service_yesterday": service_yesterday,
        "service_this_month": service_this_month,
        "service_last_month": service_last_month,

        "home_donations": home_donations,
        "service_donations": service_donations,

        "service_chart_data": json.dumps(service_chart_data),
        "home_chart_data": json.dumps(home_chart_data),

        "selected_date": selected_date.strftime("%Y-%m-%d"),
    }

    return render(
        request,
        "dashboard/Website_Donations.html",
        context,
    )