from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from decimal import Decimal
import pytz
import math
from dashboard.models import *
from website.models import *
from easypay.models import *
from receipt.models import *
from dashboard.views.auth import superuser_required

ist = pytz.timezone("Asia/Kolkata")



@superuser_required(login_url='/dashboard/login')
def admin_search_page(request):
    now = timezone.localtime(timezone.now())
    today = now.date()
    yesterday = today - timedelta(days=1)

    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = today_start + timedelta(days=1)

    yesterday_start = today_start - timedelta(days=1)
    yesterday_end = today_start

    start_of_this_month = timezone.make_aware(datetime(today.year, today.month, 1))
    end_of_this_month = (start_of_this_month + relativedelta(months=1)) - timedelta(seconds=1)

    start_of_last_month = start_of_this_month - relativedelta(months=1)
    end_of_last_month = start_of_last_month + relativedelta(months=0) - timedelta(seconds=1)

    transaction_id = request.GET.get('transaction_id', '')
    selected_branch = request.GET.get('branch', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    mobile_no = request.GET.get('mobile_no', '').strip()

    mobile_no = mobile_no.strip() if mobile_no else ''
    rm_list = RM.objects.filter(is_active=True)

    if selected_branch:
        rm_list = rm_list.filter(rm_branch=selected_branch)
    rm_list = rm_list.values('rm_code', 'rm_name').distinct()
    rm_choices = [{'rm_code': rm['rm_code'], 'virtual_label': f"{rm['rm_name']} - {rm['rm_code']}"} for rm in rm_list]

    selected_rm_code = request.GET.get('rm_code', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Default date behavior: always apply Today's date unless the user explicitly
    # selected a date (via date_from/date_to in GET). This ensures the initial page
    # load shows only today's records.
    # Transaction ID search is date-unlimited so skip this defaulting.
    has_manual_date_filter = bool(date_from or date_to)
    if not transaction_id and not has_manual_date_filter:
        date_from = today.isoformat()
        date_to = today.isoformat()


    # Only include the 4 modules requested: RM Link, GPay, Manual, Service, Home
    rmpay_qs = RMPayment.objects.filter(is_paid=True)
    gpay_qs = RMGPayPayment.objects.all()
    service_qs = ServiceDonation.objects.filter(is_paid=True)
    manual_qs = Manual80GSubmission.objects.all()
    home_qs = HomeDonation.objects.filter(is_paid=True)
   

    def normalize_mobile(v):
        if not v:
            return ''
        digits = ''.join(ch for ch in str(v) if ch.isdigit())
        return digits[-10:]


    if transaction_id:
        rmpay_qs = RMPayment.objects.all()
        gpay_qs = RMGPayPayment.objects.all()
        service_qs = ServiceDonation.objects.all()
        manual_qs = Manual80GSubmission.objects.all()
        home_qs = HomeDonation.objects.all()

        # Strict transaction id matching (no partial/contains matching)
        rmpay_qs = rmpay_qs.filter(Q(easebuzz_transaction_id__iexact=transaction_id))
        gpay_qs = gpay_qs.filter(Q(gpay_reference_id__iexact=transaction_id))
        # ServiceDonation: keep both potential transaction-id fields but match strictly
        service_qs = service_qs.filter(
            Q(easebuzz_transaction_id__iexact=transaction_id) | Q(txnid__iexact=transaction_id)
        )

        # HomeDonation: match by its transaction-id fields (txnid, easebuzz_transaction_id, receipt_no)
        home_qs = home_qs.filter(
            Q(txnid__iexact=transaction_id)
            | Q(easebuzz_transaction_id__iexact=transaction_id)
            | Q(receipt_no__iexact=transaction_id)
        )

        # Manual80GSubmission: strict match by its real transaction identifier (receipt_no)
        manual_qs = manual_qs.filter(receipt_no__iexact=transaction_id)


    if mobile_no:
        rmpay_qs = RMPayment.objects.all().filter(donor_mobile=mobile_no)
        gpay_qs = RMGPayPayment.objects.all().filter(donor_mobile=mobile_no)
        service_qs = ServiceDonation.objects.all().filter(donor_mobile=mobile_no)
        manual_qs = Manual80GSubmission.objects.all().filter(donor_mobile=mobile_no)
        home_qs = home_qs.filter(donor_mobile=mobile_no)





    if selected_branch:
        branch_rm_codes = list(RM.objects.filter(rm_branch=selected_branch).values_list('rm_code', flat=True))
        rmpay_qs = rmpay_qs.filter(rm_code__in=branch_rm_codes)
        gpay_qs = gpay_qs.filter(
            Q(rm__rm_branch=selected_branch) | Q(rm_code__in=branch_rm_codes)
        )
        # Apply branch filtering to RM-related models
        # GPay: match via FK or direct rm_code field
        # Manual/Service may not be RM-linked; they will be filtered by explicit rm_code where available

    if selected_rm_code:
        rmpay_qs = rmpay_qs.filter(rm_code=selected_rm_code)
        try:
            gpay_qs = gpay_qs.filter(
                Q(rm_code=selected_rm_code) | Q(rm__rm_code=selected_rm_code)
            )
        except Exception:
            pass
        try:
            manual_qs = manual_qs.filter(
                Q(rm_code=selected_rm_code) | Q(virtual_label__regex=rf'{selected_rm_code}$')
            )
        except Exception:
            pass
        try:
            service_qs = service_qs.filter(
                Q(rm_code=selected_rm_code) | Q(rm__rm_code=selected_rm_code)
            )
        except Exception:
            pass

    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d').date()
        except Exception:
            df = None
    else:
        df = None

    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d').date()
        except Exception:
            dt = None
    else:
        dt = None

    if df and dt:
        start_dt = timezone.make_aware(datetime.combine(df, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(dt, datetime.max.time()))

        rmpay_qs = rmpay_qs.filter(submitted_at__range=(start_dt, end_dt))
        gpay_qs = gpay_qs.filter(Q(payment_date__range=(start_dt, end_dt)) | Q(created_at__range=(start_dt, end_dt)))
        # ServiceDonation uses service_date (DateField) + created_at (DateTimeField). Use service_date for UI date filtering.
        service_qs = service_qs.filter(service_date__range=(df, dt))
        try:
            manual_qs = manual_qs.filter(donation_date__range=(df, dt))
        except Exception:
            pass
        # HomeDonation: filter by service_date when present, otherwise by submitted_at.
        home_qs = home_qs.filter(
            Q(service_date__range=(df, dt)) | Q(submitted_at__range=(start_dt, end_dt))
        )
    elif df:
        start_dt = timezone.make_aware(datetime.combine(df, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(df, datetime.max.time()))

        rmpay_qs = rmpay_qs.filter(submitted_at__range=(start_dt, end_dt))
        gpay_qs = gpay_qs.filter(Q(payment_date__range=(start_dt, end_dt)) | Q(created_at__range=(start_dt, end_dt)))
        # ServiceDonation uses service_date (DateField) for date filtering.
        service_qs = service_qs.filter(service_date__range=(df, df))
        try:
            manual_qs = manual_qs.filter(donation_date=df)
        except Exception:
            pass
        # HomeDonation: filter by service_date when present, otherwise by submitted_at.
        home_qs = home_qs.filter(
            Q(service_date=df) | Q(submitted_at__range=(start_dt, end_dt))
        )
    else:
        start_dt = None
        end_dt = None

    combined_qs = []

    seen_codes = set()
    for rp in rmpay_qs:
        # RMPayment model stores rm_code directly (no `rm` FK)
        seen_codes.add(rp.rm_code)

    for gp in gpay_qs:
        # RMGPayPayment model stores rm_code directly; it also has FK `rm`
        if getattr(gp, 'rm_code', None):
            seen_codes.add(gp.rm_code)
        if getattr(gp, 'rm', None):
            seen_codes.add(gp.rm.rm_code)

    # Service and Manual records usually don't have rm_code denormalised; they will be included when relevant

    rm_code_map = {
        c: b for c, b in RM.objects
            .filter(rm_code__in=[s for s in seen_codes if s])
            .values_list('rm_code', 'rm_branch')
    }

    def resolve_branch(rm_fk, rm_code_from_record):
        if rm_fk:
            return rm_fk.rm_branch
        code = rm_fk.rm_code if rm_fk else rm_code_from_record
        if code and code in rm_code_map:
            return rm_code_map[code]
        return '-'

    has_filter = any([
        transaction_id,
        selected_branch,
        selected_rm_code,
        date_from,
        date_to,
        mobile_no,
    ])
    if has_filter:
        for rp in rmpay_qs:
            combined_qs.append({
                'payment_status': rp.easebuzz_payment_status,
                'amount': float(rp.donor_amount),
                'virtual_label': f"{rp.rm_name} - {rp.rm_code}",
                'branch': resolve_branch(None, rp.rm_code),
                'donation_category': 'RM',
                'submitted_at': rp.submitted_at if isinstance(rp.submitted_at, datetime) else timezone.make_aware(datetime.combine(rp.submitted_at, datetime.min.time())),


                'rm_code': rp.rm_code,
                'transaction_id': rp.easebuzz_transaction_id,
                'payment_mode': rp.easebuzz_payment_mode,
                'donor_name': rp.donor_name,
                'donor_mobile': rp.donor_mobile,
                'donor_email': rp.donor_email,
                'donor_address': rp.donor_address,
            })


        for gp in gpay_qs:
            submitted = gp.payment_date or gp.created_at

            combined_qs.append({
                'payment_status': "success",
                'amount': float(gp.amount),
                'virtual_label': f"{gp.rm_name} - {gp.rm_code}",
                'branch': resolve_branch(gp.rm, gp.rm_code),
                'donation_category': 'RM',
                'submitted_at': submitted,
                'rm_code': gp.rm_code,
                'transaction_id': gp.gpay_reference_id,
                'payment_mode': "GPay",
                'donor_name': gp.donor_name,
                'donor_mobile': gp.donor_mobile,
                'donor_email': gp.donor_email or "-",
                'donor_address': gp.donor_address,
            })

        # Manual submissions
        for m in manual_qs:
            try:
                submitted_at = m.donation_date if hasattr(m, 'donation_date') else getattr(m, 'submitted_at', None)
                amount = float(getattr(m, 'donation_price', getattr(m, 'donation_amount', getattr(m, 'amount', 0))))
            except Exception:
                submitted_at = getattr(m, 'submitted_at', None)
                amount = 0
            combined_qs.append({
                'payment_status': 'success',
                'amount': amount,
                'virtual_label': '-',
                'branch': '-',
                'donation_category': 'Manual Donation',
                'submitted_at': timezone.make_aware(datetime.combine(submitted_at, datetime.min.time())) if isinstance(submitted_at, date) and not isinstance(submitted_at, datetime) else (submitted_at if timezone.is_aware(submitted_at) else timezone.make_aware(submitted_at)) if isinstance(submitted_at, datetime) else submitted_at,

                'transaction_id': getattr(m, 'receipt_no', None) or getattr(m, 'easebuzz_transaction_id', None),

                'payment_mode': getattr(m, 'easebuzz_payment_mode', None) or 'Manual',
                'donor_name': getattr(m, 'donor_name', ''),
                'donor_mobile': getattr(m, 'donor_mobile', ''),
                'donor_email': getattr(m, 'donor_email', ''),
                'donor_address': getattr(m, 'address', ''),
            })

        for sed in service_qs:
            combined_qs.append({
                'payment_status': sed.easebuzz_payment_status or ('Paid' if sed.is_paid else 'Unpaid'),
                'amount': float(sed.donation_amount),

                'virtual_label': '-',
                'branch': '-',
                'donation_category': 'Service Donation',
                'submitted_at': (
                    (timezone.make_aware(datetime.combine(sed.service_date, datetime.min.time())) if getattr(sed, 'service_date', None) and isinstance(sed.service_date, date) and not isinstance(sed.service_date, datetime) else getattr(sed, 'service_date', None))
                    or getattr(sed, 'created_at', None)
                ),

                'transaction_id': sed.easebuzz_transaction_id,
                'payment_mode': sed.easebuzz_payment_mode or 'Service',
                'donor_name': sed.donor_name,
                'donor_mobile': sed.donor_mobile,
                'donor_email': sed.donor_email,
                'donor_address': sed.address,
            })

        
        for hd in home_qs:
            combined_qs.append({
                'payment_status': hd.easebuzz_payment_status or ('Paid' if hd.is_paid else 'Unpaid'),
                'amount': float(hd.donation_amount),

                'virtual_label': '-',
                'branch': '-',
                'donation_category': 'Home Donation',
                'submitted_at': (
                    (timezone.make_aware(datetime.combine(hd.service_date, datetime.min.time())) if getattr(hd, 'service_date', None) and isinstance(hd.service_date, date) and not isinstance(hd.service_date, datetime) else getattr(hd, 'service_date', None))
                    or getattr(hd, 'created_at', None)
                ),

                'transaction_id': hd.easebuzz_transaction_id or hd.txnid,
                'payment_mode': hd.easebuzz_payment_mode or 'Home',
                'donor_name': hd.donor_name,
                'donor_mobile': hd.donor_mobile,
                'donor_email': hd.donor_email,
                'donor_address': hd.address,
            })

    

    def to_ts(v):
        if not v:
            return -math.inf
        if isinstance(v, datetime):
            if timezone.is_naive(v):
                v = timezone.make_aware(v)
            return v.timestamp()
        if isinstance(v, date):
            v = timezone.make_aware(datetime.combine(v, datetime.min.time()))
            return v.timestamp()
        return -math.inf

    try:
        if selected_branch:
            branch_rm_codes = list(RM.objects.filter(rm_branch=selected_branch).values_list('rm_code', flat=True))
            combined_qs = [x for x in combined_qs if x.get('rm_code') in branch_rm_codes]

        if selected_rm_code:
            combined_qs = [x for x in combined_qs if x.get('rm_code') == selected_rm_code]

        if mobile_no:
            search_mobile = normalize_mobile(mobile_no)
            combined_qs = [
                x for x in combined_qs
                if normalize_mobile(x.get('donor_mobile')) == search_mobile
            ]

        if 'start_dt' in locals() and 'end_dt' in locals():
            s_ts = start_dt.timestamp()
            e_ts = end_dt.timestamp()
            combined_qs = [x for x in combined_qs if s_ts <= to_ts(x.get('submitted_at')) <= e_ts]
    except Exception:
        pass

    combined_qs.sort(key=lambda x: to_ts(x['submitted_at']), reverse=True)

    def get_total(qs, start, end):
        # start/end are timezone-aware datetime objects.
        # submitted_at may be a date or datetime depending on the source model.
        total = 0
        for x in qs:
            ts = to_ts(x.get('submitted_at'))
            if ts != -math.inf:
                if start.timestamp() <= ts <= end.timestamp():
                    total += x.get('amount', 0) or 0
        return total


    today_total = get_total(combined_qs, today_start, today_end)
    yesterday_total = get_total(combined_qs, yesterday_start, yesterday_end)
    this_month_total = get_total(combined_qs, start_of_this_month, end_of_this_month)
    last_month_total = get_total(combined_qs, start_of_last_month, end_of_last_month)

    today_link_collection = sum(
        rp.donor_amount for rp in rmpay_qs
        if today_start <= rp.submitted_at < today_end
    )

    # In this limited-scope view, treat GPay as the QR collection source
    today_qr_collection = sum(
        gp.amount for gp in gpay_qs
        if (getattr(gp, 'payment_date', None) or getattr(gp, 'created_at', None)) and (today_start <= (gp.payment_date or gp.created_at) < today_end)
    )

    branches = ["madurai", "chennai", "bangalore"]
    if selected_branch:
        branches = [selected_branch]
    branch_choices = [{'value': b, 'label': b.capitalize()} for b in ["madurai", "chennai", "bangalore"]]
    branch_totals = {}

    for branch in branches:
        branch_rm_codes = list(
            RM.objects.filter(rm_branch=branch).values_list('rm_code', flat=True)
        )

        items = [x for x in combined_qs if x.get('rm_code') in branch_rm_codes]

        branch_totals[branch] = {
            'today': sum(x['amount'] for x in items if today_start <= x['submitted_at'] < today_end),
            'month': sum(x['amount'] for x in items if start_of_this_month <= x['submitted_at'] <= end_of_this_month),
        }

    for item in combined_qs:
        item.pop('rm_code', None)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'rm_donations': combined_qs,
            'rm_choices': rm_choices,
            'selected_rm_code': selected_rm_code,
            'date_from': date_from,
            'date_to': date_to,
        })

    return render(request, 'dashboard/admin_search_page.html', {
        'rm_donations': combined_qs,
        'today_total': today_total,
        'yesterday_total': yesterday_total,
        'this_month_total': this_month_total,
        'last_month_total': last_month_total,
        'rm_choices': rm_choices,
        'selected_rm_code': selected_rm_code,
        'branch_totals': branch_totals,
        'today_link_collection': today_link_collection,
        'today_qr_collection': today_qr_collection,
        'transaction_id': transaction_id,
        'selected_branch': selected_branch,
        'date_from': date_from,
        'date_to': date_to,
        'branch_choices': branch_choices,
        'mobile_no': mobile_no,
    })