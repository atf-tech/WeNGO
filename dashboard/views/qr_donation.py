from datetime import timedelta
import calendar

from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from dashboard.models import RM
from easypay.models import RMPayment, RMGPayPayment


def qr_donation(request):
    selected_rm_code = request.GET.get("rm_code", "")
    selected_date_str = request.GET.get("selected_date", "")



    def _start_of_day(d):
        local_dt = timezone.make_aware(
            timezone.datetime.combine(d, timezone.datetime.min.time()),
            timezone.get_current_timezone(),
        )
        return local_dt

    def _start_of_month(d):
        return _start_of_day(d.replace(day=1))

    def _add_months(d, months):
        month = d.month - 1 + months
        year = d.year + month // 12
        month = month % 12 + 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        return d.replace(year=year, month=month, day=day)

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    # Built-in dashboard ranges
    start_today = _start_of_day(today)
    start_tomorrow = _start_of_day(today + timedelta(days=1))

    start_yesterday = _start_of_day(yesterday)

    start_this_month = _start_of_month(today)
    start_next_month = _start_of_day(_add_months(today, 1).replace(day=1))

    last_month_start = _start_of_month(_add_months(today.replace(day=1), -1))

    # Keep for calculations
    start_of_month = start_this_month
    end_of_month = start_next_month
    start_of_last_month = last_month_start
    end_of_last_month = start_of_month

    # Parse selected_date (single day or range)
    def _parse_selected_date_range(selected_date):
        selected_date = (selected_date or "").strip()
        if not selected_date:
            return None

        # Support both:
        # - "01 Jul, 2026 - 04 Jul, 2026"
        # - "01 Jul, 2026 to 04 Jul, 2026" (flatpickr default for range)
        if " - " in selected_date:
            start_part, end_part = selected_date.split(" - ", 1)
        elif " to " in selected_date:
            start_part, end_part = selected_date.split(" to ", 1)
        else:
            start_part = selected_date
            end_part = selected_date

        start_part = start_part.strip()
        end_part = end_part.strip()

        if not start_part:
            return None

        # If only a single date was provided, treat as a single day.
        if not end_part:
            end_part = start_part

        try:
            start_date = timezone.datetime.strptime(start_part, "%d %b, %Y").date()
            end_date = timezone.datetime.strptime(end_part, "%d %b, %Y").date()
        except (ValueError, TypeError):
            return None

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        start_dt = _start_of_day(start_date)
        end_dt_exclusive = _start_of_day(end_date + timedelta(days=1))
        return start_dt, end_dt_exclusive



    parsed_date_range = _parse_selected_date_range(selected_date_str)

    # Default filters: Date = Today on first page load (when no selected_date provided)
    active_date_range = parsed_date_range or (  # single source of truth for date filtering
        _start_of_day(today),
        _start_of_day(today + timedelta(days=1)),
    )

    link_qs = RMPayment.objects.all()
    gpay_qs = RMGPayPayment.objects.all()

    if selected_rm_code:
        link_qs = link_qs.filter(rm_code=selected_rm_code)
        gpay_qs = gpay_qs.filter(rm_code=selected_rm_code)



    active_start_dt, active_end_exclusive_dt = active_date_range
    link_qs = link_qs.filter(
        submitted_at__gte=active_start_dt,
        submitted_at__lt=active_end_exclusive_dt,
    )
    gpay_qs = gpay_qs.filter(
        payment_date__gte=active_start_dt,
        payment_date__lt=active_end_exclusive_dt,
    )


    rm_by_code = {rm.rm_code: rm for rm in RM.objects.all()}

    link_today = link_qs.aggregate(total=Sum("donor_amount"))["total"] or 0
    gpay_today = gpay_qs.aggregate(total=Sum("amount"))["total"] or 0

    today_collection = link_today + gpay_today
    yesterday_collection = today_collection
    this_month_collection = today_collection
    last_month_collection = today_collection



    madurai_link = 0
    chennai_link = 0
    bangalore_link = 0

    madurai_gpay = 0
    chennai_gpay = 0
    bangalore_gpay = 0

    for payment in link_qs:
        rm = rm_by_code.get(payment.rm_code)
        if not rm:
            continue
        branch = (rm.rm_branch or "").strip().lower()
        if branch == "madurai":
            madurai_link += payment.donor_amount or 0
        elif branch == "chennai":
            chennai_link += payment.donor_amount or 0
        elif branch == "bangalore":
            bangalore_link += payment.donor_amount or 0

    for payment in gpay_qs:
        rm = rm_by_code.get(payment.rm_code)
        if not rm:
            continue
        branch = (rm.rm_branch or "").strip().lower()
        if branch == "madurai":
            madurai_gpay += payment.amount or 0
        elif branch == "chennai":
            chennai_gpay += payment.amount or 0
        elif branch == "bangalore":
            bangalore_gpay += payment.amount or 0

    madurai_today = madurai_link + madurai_gpay
    chennai_today = chennai_link + chennai_gpay
    bangalore_today = bangalore_link + bangalore_gpay
    all_branches_today = madurai_today + chennai_today + bangalore_today


    rm_donations = []

    for payment in link_qs:
        rm = rm_by_code.get(payment.rm_code)
        rm_donations.append(
            {
                "virtual_label": f"{payment.rm_name} - {payment.rm_code}",
                "receipt_no": payment.receipt_no,
                "donor_name": payment.donor_name,
                "rm_name": payment.rm_name,
                "package_type": payment.package_type,
                "submitted_at": payment.submitted_at,
                "payment_status": payment.easebuzz_payment_status,
                "source": "Link",
                "amount": payment.donor_amount,
                "donor_mobile": payment.donor_mobile,
                "donor_email": payment.donor_email,
                "donor_address": payment.donor_address,
                "rm_code": payment.rm_code,
                "branch": rm.get_rm_branch_display() if rm else "-",
                "payment_mode": payment.easebuzz_payment_mode,
                "transaction_id": payment.easebuzz_transaction_id,
                "unique_transaction_id": payment.txnid,
            }
        )

    for payment in gpay_qs:
        rm = rm_by_code.get(payment.rm_code)
        rm_donations.append(
            {
                "virtual_label": f"{payment.rm_name} - {payment.rm_code}",
                "receipt_no": payment.receipt_no,
                "donor_name": payment.donor_name,
                "rm_name": payment.rm_name,
                "package_type": payment.package_type,
                "submitted_at": payment.payment_date,
                "payment_status": "Success",
                "source": "GPay",
                "amount": payment.amount,
                "donor_mobile": payment.donor_mobile,
                "donor_email": payment.donor_email,
                "donor_address": payment.donor_address,
                "rm_code": payment.rm_code,
                "branch": rm.get_rm_branch_display() if rm else "-",
                "payment_mode": "UPI",
                "transaction_id": payment.gpay_reference_id,
                "unique_transaction_id": payment.gpay_reference_id,
            }
        )

    # Latest first (sorting by latest submission)
    rm_donations = sorted(rm_donations, key=lambda x: x["submitted_at"], reverse=True)

    # Template expects rm_list + stateful params
    rm_list = list(RM.objects.all())

    return render(
        request,
        "dashboard/qr_donation.html",
        {
            "rm_list": rm_list,
            "selected_rm_code": selected_rm_code,
            "selected_date_str": selected_date_str,
            "rm_donations": rm_donations,
            "today_collection": today_collection,
            "yesterday_collection": yesterday_collection,
            "this_month_collection": this_month_collection,
            "last_month_collection": last_month_collection,
            "link_today": link_today,
            "gpay_today": gpay_today,
            "total_today": today_collection,
            "madurai_today": madurai_today,
            "chennai_today": chennai_today,
            "bangalore_today": bangalore_today,
            "all_branches_today": all_branches_today,
            # used by template fallback (keep existing key name)
            "filter_start_date": today,
        },
    )

