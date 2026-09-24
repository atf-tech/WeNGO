from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Value, CharField, F, Q, Avg, Count, Max
from django.urls import reverse
from datetime import datetime, date, timedelta
from collections import defaultdict
import pytz

from dashboard.models import RM
from RMPortal.models import Conversation, Message, MessageMedia, Donor, BlockedContact

ist = pytz.timezone("Asia/Kolkata")


def _day_range(date):
    start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
    return start, start + timedelta(days=1)


def _custom_range(from_str, to_str):
    try:
        from_d = datetime.strptime(from_str, "%Y-%m-%d").date()
        to_d = datetime.strptime(to_str, "%Y-%m-%d").date()
        return _day_range(from_d)[0], _day_range(to_d)[1]
    except (ValueError, TypeError):
        return None, None


def _ranges():
    now = timezone.now()
    today = now.date()
    yesterday = today - timedelta(days=1)

    today_start, today_end = _day_range(today)
    yesterday_start, yesterday_end = _day_range(yesterday)

    week_start_date = today - timedelta(days=today.weekday())
    week_start = timezone.make_aware(datetime.combine(week_start_date, datetime.min.time()))

    month_start = timezone.make_aware(datetime.combine(today.replace(day=1), datetime.min.time()))

    first_of_this_month = today.replace(day=1)
    last_month_end_date = first_of_this_month - timedelta(days=1)
    last_month_start = timezone.make_aware(datetime.combine(last_month_end_date.replace(day=1), datetime.min.time()))
    last_month_end = timezone.make_aware(datetime.combine(first_of_this_month, datetime.min.time()))

    last_week_end = week_start
    last_week_start = last_week_end - timedelta(days=7)

    return {
        "now": now,
        "today": today,
        "today_start": today_start,
        "today_end": today_end,
        "yesterday_start": yesterday_start,
        "yesterday_end": yesterday_end,
        "week_start": week_start,
        "month_start": month_start,
        "last_month_start": last_month_start,
        "last_month_end": last_month_end,
        "last_week_start": last_week_start,
        "last_week_end": last_week_end,
    }


def _pct_change(curr, prev):
    if prev == 0:
        return {"value": 0, "status": "neutral"}
    pct = round(((curr - prev) / prev) * 100, 1)
    return {"value": abs(pct), "status": "positive" if pct >= 0 else "negative"}


def _rm_qs(branch=""):
    qs = RM.objects.all()
    if branch:
        qs = qs.filter(rm_branch=branch)
    return qs


def _avg_response_minutes(rm=None, since=None, until=None):
    conv_qs = Conversation.objects.all()
    if rm:
        conv_qs = conv_qs.filter(rm=rm)
    if since:
        conv_qs = conv_qs.filter(created_at__gte=since)
    if until:
        conv_qs = conv_qs.filter(created_at__lt=until)

    conv_ids = list(conv_qs.values_list("id", flat=True)[:200])
    if not conv_ids:
        return None

    first_in = {}
    first_reply = {}
    rows = (
        Message.objects.filter(
            conversation_id__in=conv_ids,
            direction__in=("in", "out"),
        )
        .order_by("created_at")
        .values_list("conversation_id", "direction", "created_at")
    )
    for conv_id, direction, created_at in rows:
        if direction == "in":
            first_in.setdefault(conv_id, created_at)
        else:
            inbound = first_in.get(conv_id)
            if inbound is not None and created_at > inbound:
                first_reply.setdefault(conv_id, created_at)

    total_minutes = 0
    count = 0
    for conv_id, inbound in first_in.items():
        reply = first_reply.get(conv_id)
        if not reply:
            continue
        diff = (reply - inbound).total_seconds() / 60
        if diff <= 1440:
            total_minutes += diff
            count += 1

    return round(total_minutes / count, 1) if count else None


@login_required(login_url="/dashboard/login")
def whatsapp_api(request):
    branches = RM.BRANCH_CHOICES
    rm_objects = (
        RM.objects.annotate(_conv_count=Count("conversations"))
        .filter(Q(is_active=True) | Q(_conv_count__gt=0))
        .order_by("rm_branch", "rm_name")
    )
    context = {
        "branches": branches,
        "rm_objects": rm_objects,
        "default_branch": "",
        "total_rms": rm_objects.count(),
        "wa_rms": rm_objects.filter(active_whatsapp=True).count(),
    }
    return render(request, "dashboard/whatsapp_api.html", context)


def _api_period_filter(request, default_since_fn, default_until_fn):
    r = _ranges()
    period = request.GET.get("period", "today")
    branch = request.GET.get("branch", "")

    period_map = {
        "today": (r["today_start"], r["today_end"]),
        "yesterday": (r["yesterday_start"], r["yesterday_end"]),
        "week": (r["week_start"], r["now"]),
        "month": (r["month_start"], r["now"]),
    }
    if period == "custom":
        since, until = _custom_range(request.GET.get("from", ""), request.GET.get("to", ""))
        if since is None:
            since, until = default_since_fn(r), default_until_fn(r)
    else:
        since, until = period_map.get(period, (r["today_start"], r["today_end"]))

    return since, until, period, branch, r


def api_kpi_data(request):
    since, until, period, branch, r = _api_period_filter(request, lambda r: r["today_start"], lambda r: r["today_end"])

    rm_ids = list(_rm_qs(branch).values_list("id", flat=True))
    conv_qs = Conversation.objects.filter(rm_id__in=rm_ids)
    msg_qs = Message.objects.filter(conversation__rm_id__in=rm_ids)

    leads_period = conv_qs.filter(created_at__gte=since, created_at__lt=until).count()
    leads_today = conv_qs.filter(created_at__gte=r["today_start"], created_at__lt=r["today_end"]).count()
    leads_yesterday = conv_qs.filter(created_at__gte=r["yesterday_start"], created_at__lt=r["yesterday_end"]).count()
    leads_week = conv_qs.filter(created_at__gte=r["week_start"]).count()
    leads_month = conv_qs.filter(created_at__gte=r["month_start"]).count()
    leads_lastmonth = conv_qs.filter(created_at__gte=r["last_month_start"], created_at__lt=r["last_month_end"]).count()
    leads_lastweek = conv_qs.filter(created_at__gte=r["last_week_start"], created_at__lt=r["last_week_end"]).count()

    recv_period = msg_qs.filter(direction="in", created_at__gte=since, created_at__lt=until).count()
    sent_period = msg_qs.filter(direction="out", created_at__gte=since, created_at__lt=until).count()

    total_convs = conv_qs.count()
    replied_convs = conv_qs.filter(messages__direction="out").distinct().count()
    reply_rate = round((replied_convs / total_convs * 100), 1) if total_convs else 0

    donors_period = Donor.objects.filter(created_at__gte=since, created_at__lt=until).count()
    conversion_rate = round((donors_period / leads_period * 100), 1) if leads_period else 0

    active_rms_today = conv_qs.filter(last_message_at__gte=r["today_start"]).values("rm_id").distinct().count()

    open_convs = conv_qs.filter(status="open").count()
    closed_convs = conv_qs.filter(status="closed").count()

    avg_resp = _avg_response_minutes(since=since, until=until)

    return JsonResponse({
        "leads": {
            "period": leads_period,
            "today": leads_today,
            "yesterday": leads_yesterday,
            "week": leads_week,
            "month": leads_month,
            "last_month": leads_lastmonth,
            "week_change": _pct_change(leads_week, leads_lastweek),
            "month_change": _pct_change(leads_month, leads_lastmonth),
            "today_change": _pct_change(leads_today, leads_yesterday),
        },
        "messages": {
            "received_period": recv_period,
            "sent_period": sent_period,
        },
        "conversations": {
            "total": total_convs,
            "open": open_convs,
            "closed": closed_convs,
            "replied": replied_convs,
        },
        "reply_rate": reply_rate,
        "conversion_rate": conversion_rate,
        "donors_period": donors_period,
        "total_donors": Donor.objects.count(),
        "active_rms_today": active_rms_today,
        "avg_response_min": avg_resp,
        "rms": {
            "total": len(rm_ids),
            "active_wa": _rm_qs(branch).filter(active_whatsapp=True).count(),
        },
    })


def api_branch_chart(request):
    since, until, period, branch, r = _api_period_filter(request, lambda r: r["week_start"], lambda r: r["now"])

    labels, leads_data, recv_data, sent_data, conv_data = [], [], [], [], []

    for code, label in RM.BRANCH_CHOICES:
        b_rm_ids = list(RM.objects.filter(rm_branch=code).values_list("id", flat=True))
        b_convs = Conversation.objects.filter(rm_id__in=b_rm_ids)
        b_msgs = Message.objects.filter(conversation__rm_id__in=b_rm_ids)

        leads = b_convs.filter(created_at__gte=since, created_at__lt=until).count()
        recv = b_msgs.filter(direction="in", created_at__gte=since, created_at__lt=until).count()
        sent = b_msgs.filter(direction="out", created_at__gte=since, created_at__lt=until).count()

        all_phones = b_convs.values_list("donor__phone_number", flat=True)
        donors = Donor.objects.filter(phone_number__in=all_phones, created_at__gte=since, created_at__lt=until).count()
        conv_rate = round((donors / leads * 100), 1) if leads else 0

        labels.append(label)
        leads_data.append(leads)
        recv_data.append(recv)
        sent_data.append(sent)
        conv_data.append(conv_rate)

    return JsonResponse({
        "labels": labels,
        "leads": leads_data,
        "received": recv_data,
        "sent": sent_data,
        "conversion_rate": conv_data,
    })


def api_trend_chart(request):
    since, until, period, branch, r = _api_period_filter(request, lambda r: r["week_start"], lambda r: r["now"])
    ctype = request.GET.get("type", "daily")

    rm_ids = list(_rm_qs(branch).values_list("id", flat=True))
    conv_qs = Conversation.objects.filter(rm_id__in=rm_ids)
    msg_qs = Message.objects.filter(conversation__rm_id__in=rm_ids)

    labels, leads_data, recv_data, sent_data = [], [], [], []

    if ctype == "daily":
        for i in range(13, -1, -1):
            d = r["today"] - timedelta(days=i)
            s, e = _day_range(d)
            labels.append(d.strftime("%d %b"))
            leads_data.append(conv_qs.filter(created_at__gte=s, created_at__lt=e).count())
            recv_data.append(msg_qs.filter(direction="in", created_at__gte=s, created_at__lt=e).count())
            sent_data.append(msg_qs.filter(direction="out", created_at__gte=s, created_at__lt=e).count())
    elif ctype == "weekly":
        for i in range(7, -1, -1):
            w_end = r["week_start"] + timedelta(weeks=(1 - i))
            w_start = w_end - timedelta(weeks=1)
            labels.append(f"Wk {8 - i}")
            leads_data.append(conv_qs.filter(created_at__gte=w_start, created_at__lt=w_end).count())
            recv_data.append(msg_qs.filter(direction="in", created_at__gte=w_start, created_at__lt=w_end).count())
            sent_data.append(msg_qs.filter(direction="out", created_at__gte=w_start, created_at__lt=w_end).count())
    elif ctype == "monthly":
        for i in range(5, -1, -1):
            ref = r["today"].replace(day=1)
            for _ in range(i):
                ref = (ref - timedelta(days=1)).replace(day=1)
            m_start = timezone.make_aware(datetime.combine(ref, datetime.min.time()))
            next_m = (ref.replace(day=28) + timedelta(days=4)).replace(day=1)
            m_end = timezone.make_aware(datetime.combine(next_m, datetime.min.time()))
            labels.append(ref.strftime("%b %Y"))
            leads_data.append(conv_qs.filter(created_at__gte=m_start, created_at__lt=m_end).count())
            recv_data.append(msg_qs.filter(direction="in", created_at__gte=m_start, created_at__lt=m_end).count())
            sent_data.append(msg_qs.filter(direction="out", created_at__gte=m_start, created_at__lt=m_end).count())

    return JsonResponse({
        "labels": labels,
        "leads": leads_data,
        "received": recv_data,
        "sent": sent_data,
    })


def api_rm_table(request):
    since, until, period, branch, r = _api_period_filter(request, lambda r: r["today_start"], lambda r: r["today_end"])
    rm_status = request.GET.get("rm_status", "active")
    rm_code = request.GET.get("rm_code", "")

    rm_query = _rm_qs(branch)
    if rm_code:
        rm_query = rm_query.filter(rm_code=rm_code)
    elif rm_status == "active":
        rm_query = rm_query.filter(is_active=True)
    elif rm_status == "inactive":
        rm_query = rm_query.filter(is_active=False)

    rows = []
    for rm in rm_query.order_by("rm_branch", "rm_name"):
        convs = Conversation.objects.filter(rm=rm)
        msgs = Message.objects.filter(conversation__rm=rm)

        leads = convs.filter(created_at__gte=since, created_at__lt=until).count()
        received = msgs.filter(direction="in", created_at__gte=since, created_at__lt=until).count()
        sent = msgs.filter(direction="out", created_at__gte=since, created_at__lt=until).count()

        total_convs = convs.count()
        replied_convs = convs.filter(messages__direction="out").distinct().count()
        reply_rate = round((replied_convs / total_convs * 100), 1) if total_convs else 0

        open_c = convs.filter(status="open").count()
        closed_c = convs.filter(status="closed").count()

        rm_phones = convs.values_list("donor__phone_number", flat=True)
        converted = Donor.objects.filter(phone_number__in=rm_phones, created_at__gte=since, created_at__lt=until).count()
        conv_rate = round((converted / leads * 100), 1) if leads else 0

        avg_resp = _avg_response_minutes(rm=rm, since=since, until=until)

        last_msg = msgs.order_by("-created_at").first()
        last_active = timezone.localtime(last_msg.created_at).strftime("%d %b %I:%M %p") if last_msg else "—"

        rows.append({
            "rm_name": rm.rm_name,
            "rm_code": rm.rm_code,
            "rm_branch": rm.get_rm_branch_display() if rm.rm_branch else "—",
            "rm_branch_code": rm.rm_branch or "",
            "tl_name": rm.tl_name or "—",
            "active_wa": rm.active_whatsapp,
            "leads": leads,
            "received": received,
            "sent": sent,
            "reply_rate": reply_rate,
            "conv_rate": conv_rate,
            "avg_resp_min": avg_resp,
            "open": open_c,
            "closed": closed_c,
            "last_active": last_active,
        })

    rows.sort(key=lambda x: x["leads"], reverse=True)
    for i, row in enumerate(rows, 1):
        row["rank"] = i

    return JsonResponse({"rows": rows, "period": period})


def api_response_time(request):
    since, until, period, branch, r = _api_period_filter(request, lambda r: r["week_start"], lambda r: r["now"])

    labels, values, colors = [], [], []
    for rm in _rm_qs(branch).order_by("rm_name"):
        avg = _avg_response_minutes(rm=rm, since=since, until=until)
        if avg is None:
            continue
        labels.append(f"{rm.rm_name} ({rm.rm_code})")
        values.append(avg)
        colors.append("#0ab39c" if avg < 5 else "#f7b84b" if avg < 15 else "#f06548")

    return JsonResponse({"labels": labels, "values": values, "colors": colors})


def api_conversion_funnel(request):
    since, until, period, branch, r = _api_period_filter(request, lambda r: r["month_start"], lambda r: r["now"])

    rm_ids = list(_rm_qs(branch).values_list("id", flat=True))
    conv_qs = Conversation.objects.filter(rm_id__in=rm_ids)

    leads = conv_qs.filter(created_at__gte=since, created_at__lt=until).count()
    replied = conv_qs.filter(created_at__gte=since, created_at__lt=until, messages__direction="out").distinct().count()

    all_phones = conv_qs.values_list("donor__phone_number", flat=True)
    converted = Donor.objects.filter(phone_number__in=all_phones, created_at__gte=since, created_at__lt=until).count()

    return JsonResponse({
        "stages": [
            {"label": "Total Leads", "value": leads, "pct": 100},
            {"label": "Replied by RM", "value": replied, "pct": round(replied / leads * 100, 1) if leads else 0},
            {"label": "Donors Registered", "value": converted, "pct": round(converted / leads * 100, 1) if leads else 0},
        ]
    })


def _conv_first_reply_min(conv):
    first_in = Message.objects.filter(conversation=conv, direction="in").order_by("created_at").values_list("created_at", flat=True).first()
    if not first_in:
        return None
    first_out = Message.objects.filter(conversation=conv, direction="out", created_at__gt=first_in).order_by("created_at").values_list("created_at", flat=True).first()
    if not first_out:
        return None
    diff = (first_out - first_in).total_seconds() / 60
    return round(diff, 1) if diff <= 1440 else None


def _msg_reply_min(msg, conv):
    if msg.direction != "in":
        return None
    nxt = Message.objects.filter(conversation=conv, direction="out", created_at__gt=msg.created_at).order_by("created_at").values_list("created_at", flat=True).first()
    if not nxt:
        return None
    diff = (nxt - msg.created_at).total_seconds() / 60
    return round(diff, 1) if diff <= 1440 else None


def _get_msg_body(msg):
    for attr in ("body", "content", "message", "text"):
        val = getattr(msg, attr, None)
        if val:
            return str(val)
    return ""


@login_required(login_url="/dashboard/login")
def rm_analytics_detailed(request, rm_code):
    rm = get_object_or_404(RM, rm_code=rm_code)
    return render(request, "dashboard/rm_analytics_detailed.html", {"rm": rm})


def api_rm_detail_profile(request, rm_code):
    from django.shortcuts import get_object_or_404
    rm = get_object_or_404(RM, rm_code=rm_code)
    convs = Conversation.objects.filter(rm=rm)
    msgs = Message.objects.filter(conversation__rm=rm)

    return JsonResponse({
        "total_leads": convs.count(),
        "total_sent": msgs.filter(direction="out").count(),
        "total_recv": msgs.filter(direction="in").count(),
        "avg_resp_min": _avg_response_minutes(rm=rm),
    })


def api_rm_detail_stats(request, rm_code):
    from django.shortcuts import get_object_or_404
    rm = get_object_or_404(RM, rm_code=rm_code)
    r = _ranges()

    convs = Conversation.objects.filter(rm=rm)
    msgs = Message.objects.filter(conversation__rm=rm)

    first_this_month = r["today"].replace(day=1)
    lm_end_date = first_this_month - timedelta(days=1)
    lm_s = timezone.make_aware(datetime.combine(lm_end_date.replace(day=1), datetime.min.time()))
    lm_e = timezone.make_aware(datetime.combine(first_this_month, datetime.min.time()))

    def bucket(since, until):
        return {
            "received": msgs.filter(direction="in", created_at__gte=since, created_at__lt=until).count(),
            "sent": msgs.filter(direction="out", created_at__gte=since, created_at__lt=until).count(),
            "leads": convs.filter(created_at__gte=since, created_at__lt=until).count(),
        }

    return JsonResponse({
        "today": bucket(r["today_start"], r["today_end"]),
        "yesterday": bucket(r["yesterday_start"], r["yesterday_end"]),
        "week": bucket(r["week_start"], r["now"]),
        "month": bucket(r["month_start"], r["now"]),
        "last_month": bucket(lm_s, lm_e),
    })


def api_rm_detail_trend(request, rm_code):
    from django.shortcuts import get_object_or_404
    rm = get_object_or_404(RM, rm_code=rm_code)
    r = _ranges()

    convs = Conversation.objects.filter(rm=rm)
    msgs = Message.objects.filter(conversation__rm=rm)

    trend_range = request.GET.get("trend_range", "today")
    custom_from = request.GET.get("from", "")
    custom_to = request.GET.get("to", "")

    week_start_date = r["today"] - timedelta(days=r["today"].weekday())
    last_week_end = timezone.make_aware(datetime.combine(week_start_date, datetime.min.time()))
    last_week_start = last_week_end - timedelta(days=7)

    first_this_month = r["today"].replace(day=1)
    lm_end_d = first_this_month - timedelta(days=1)
    lm_s = timezone.make_aware(datetime.combine(lm_end_d.replace(day=1), datetime.min.time()))
    lm_e = timezone.make_aware(datetime.combine(first_this_month, datetime.min.time()))

    if trend_range == "custom" and custom_from and custom_to:
        try:
            from_d = datetime.strptime(custom_from, "%Y-%m-%d").date()
            to_d = datetime.strptime(custom_to, "%Y-%m-%d").date()
            days = (to_d - from_d).days + 1
            date_points = [(from_d + timedelta(days=i), (from_d + timedelta(days=i)).strftime("%d %b")) for i in range(min(days, 90))]
        except ValueError:
            date_points = []
    elif trend_range == "today":
        hours = []
        for h in range(24):
            hs = timezone.make_aware(datetime.combine(r["today"], datetime.min.time())) + timedelta(hours=h)
            he = hs + timedelta(hours=1)
            hours.append((hs, he, f"{h:02d}:00"))
        labels, recv_data, sent_data, leads_data = [], [], [], []
        for hs, he, lbl in hours:
            labels.append(lbl)
            recv_data.append(msgs.filter(direction="in", created_at__gte=hs, created_at__lt=he).count())
            sent_data.append(msgs.filter(direction="out", created_at__gte=hs, created_at__lt=he).count())
            leads_data.append(convs.filter(created_at__gte=hs, created_at__lt=he).count())
        return JsonResponse({"labels": labels, "received": recv_data, "sent": sent_data, "leads": leads_data})
    elif trend_range == "yesterday":
        hours = []
        for h in range(24):
            hs = timezone.make_aware(datetime.combine(r["today"] - timedelta(days=1), datetime.min.time())) + timedelta(hours=h)
            he = hs + timedelta(hours=1)
            hours.append((hs, he, f"{h:02d}:00"))
        labels, recv_data, sent_data, leads_data = [], [], [], []
        for hs, he, lbl in hours:
            labels.append(lbl)
            recv_data.append(msgs.filter(direction="in", created_at__gte=hs, created_at__lt=he).count())
            sent_data.append(msgs.filter(direction="out", created_at__gte=hs, created_at__lt=he).count())
            leads_data.append(convs.filter(created_at__gte=hs, created_at__lt=he).count())
        return JsonResponse({"labels": labels, "received": recv_data, "sent": sent_data, "leads": leads_data})
    else:
        range_map = {
            "week": (r["week_start"], r["now"], 7),
            "last_week": (last_week_start, last_week_end, 7),
            "month": (r["month_start"], r["now"], None),
            "last_month": (lm_s, lm_e, None),
        }
        since, until, n_days = range_map.get(trend_range, (r["week_start"], r["now"], 7))
        if n_days is None:
            n_days = (until.date() - since.date()).days + 1
        date_points = [(since.date() + timedelta(days=i), (since.date() + timedelta(days=i)).strftime("%d %b")) for i in range(min(n_days, 90))]

    labels, recv_data, sent_data, leads_data = [], [], [], []
    for d_obj, lbl in date_points:
        s, e = _day_range(d_obj)
        labels.append(lbl)
        recv_data.append(msgs.filter(direction="in", created_at__gte=s, created_at__lt=e).count())
        sent_data.append(msgs.filter(direction="out", created_at__gte=s, created_at__lt=e).count())
        leads_data.append(convs.filter(created_at__gte=s, created_at__lt=e).count())

    return JsonResponse({"labels": labels, "received": recv_data, "sent": sent_data, "leads": leads_data})


def api_rm_detail_conversations(request, rm_code):
    from django.shortcuts import get_object_or_404
    rm = get_object_or_404(RM, rm_code=rm_code)
    r = _ranges()
    period = request.GET.get("period", "today")

    first_this_month = r["today"].replace(day=1)
    lm_end_date = first_this_month - timedelta(days=1)
    lm_s = timezone.make_aware(datetime.combine(lm_end_date.replace(day=1), datetime.min.time()))
    lm_e = timezone.make_aware(datetime.combine(first_this_month, datetime.min.time()))

    period_map = {
        "today": (r["today_start"], r["today_end"]),
        "yesterday": (r["yesterday_start"], r["yesterday_end"]),
        "week": (r["week_start"], r["now"]),
        "month": (r["month_start"], r["now"]),
        "last_month": (lm_s, lm_e),
    }
    since, until = period_map.get(period, (r["today_start"], r["today_end"]))

    convs = Conversation.objects.filter(rm=rm, created_at__gte=since, created_at__lt=until).select_related("donor").order_by("-created_at")

    rows = []
    for conv in convs:
        m_qs = Message.objects.filter(conversation=conv).order_by("created_at")
        in_count = m_qs.filter(direction="in").count()
        out_count = m_qs.filter(direction="out").count()
        first_m = m_qs.first()
        last_m = m_qs.last()

        rows.append({
            "id": conv.id,
            "donor_name": getattr(conv.donor, "donor_name", None) or "Unknown",
            "donor_phone": getattr(conv.donor, "phone_number", None) or "—",
            "first_msg_time": timezone.localtime(first_m.created_at).strftime("%d %b %I:%M %p") if first_m else "—",
            "last_msg_time": timezone.localtime(last_m.created_at).strftime("%d %b %I:%M %p") if last_m else "—",
            "total_msgs": in_count + out_count,
            "in_count": in_count,
            "out_count": out_count,
            "reply_time_min": _conv_first_reply_min(conv),
            "status": conv.status or "open",
        })

    return JsonResponse({"conversations": rows, "total": len(rows), "period": period})


def api_rm_detail_conv_messages(request, rm_code, conv_id):
    from django.shortcuts import get_object_or_404
    rm = get_object_or_404(RM, rm_code=rm_code)
    conv = get_object_or_404(Conversation, id=conv_id, rm=rm)

    msgs = Message.objects.filter(conversation=conv).order_by("created_at")

    return JsonResponse({
        "conv_id": conv_id,
        "messages": [{
            "id": msg.id,
            "created_at": timezone.localtime(msg.created_at).strftime("%d %b %Y, %I:%M:%S %p"),
            "direction": msg.direction,
            "body": _get_msg_body(msg),
            "reply_time_min": _msg_reply_min(msg, conv),
        } for msg in msgs],
    })


DONOR_SEARCH_MSG_CAP = 2000


def _digits_only(value):
    import re
    return re.sub(r"\D", "", str(value or ""))


def _pretty_phone(phone):
    d = _digits_only(phone)
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 10:
        return f"+91 {d[:5]} {d[5:]}"
    return phone or "-"


def _fmt_dt(dt, fmt="%d %b %Y, %I:%M:%S %p"):
    return timezone.localtime(dt).strftime(fmt) if dt else None


def _minutes_between(a, b):
    if not a or not b:
        return None
    return round((b - a).total_seconds() / 60, 1)


def api_donor_search(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < 3:
        return JsonResponse({
            "found": False,
            "error": "Type at least 3 characters of the donor's mobile number.",
        })

    digits = _digits_only(q)

    if digits:
        if len(digits) >= 10:
            donors_qs = Donor.objects.filter(phone_number__endswith=digits[-10:])
        else:
            donors_qs = Donor.objects.filter(phone_number__contains=digits)
    else:
        donors_qs = Donor.objects.filter(phone_number__icontains=q)

    donors = list(donors_qs.order_by("phone_number")[:30])

    if not donors:
        return JsonResponse({
            "found": False,
            "error": f"No donor found for \"{q}\".",
        })

    if len(donors) > 1:
        rows = []
        for d in donors:
            last = Message.objects.filter(conversation__donor=d).order_by("-created_at").values_list("created_at", flat=True).first()
            rows.append({
                "phone": d.phone_number,
                "phone_fmt": _pretty_phone(d.phone_number),
                "name": "Unknown",
                "conv_count": Conversation.objects.filter(donor=d).count(),
                "last_msg_at": _fmt_dt(last, "%d %b %Y, %I:%M %p") or "-",
            })
        return JsonResponse({
            "found": False,
            "multiple": True,
            "message": f"{len(donors)} donors match \"{q}\". Pick one:",
            "matches": rows,
        })

    donor = donors[0]

    convs = list(Conversation.objects.filter(donor=donor).select_related("rm").order_by("created_at"))
    conv_ids = [c.id for c in convs]

    msgs = list(Message.objects.filter(conversation_id__in=conv_ids).select_related("media").order_by("-created_at", "-id")[:DONOR_SEARCH_MSG_CAP])
    msgs.reverse()

    by_conv = defaultdict(list)
    for m in msgs:
        by_conv[m.conversation_id].append(m)

    conv_rows = []
    rm_agg = {}
    tot_in = tot_out = 0
    first_contact = last_contact = None
    reply_mins = []

    for conv in convs:
        cmsgs = by_conv.get(conv.id, [])
        in_count = sum(1 for m in cmsgs if m.direction == "in")
        out_count = len(cmsgs) - in_count
        first_m = cmsgs[0] if cmsgs else None
        last_m = cmsgs[-1] if cmsgs else None

        first_in = next((m for m in cmsgs if m.direction == "in"), None)
        first_out = next((m for m in cmsgs if m.direction == "out" and first_in and m.created_at > first_in.created_at), None)
        c_reply = _minutes_between(first_in.created_at, first_out.created_at) if first_out else None
        if c_reply is not None and c_reply > 1440:
            c_reply = None
        if c_reply is not None:
            reply_mins.append(c_reply)

        msg_rows = []
        for idx, m in enumerate(cmsgs):
            r_min = None
            if m.direction == "in":
                nxt = next((n for n in cmsgs[idx + 1:] if n.direction == "out"), None)
                if nxt:
                    r_min = _minutes_between(m.created_at, nxt.created_at)
                    if r_min is not None and r_min > 1440:
                        r_min = None
            prev = cmsgs[idx - 1] if idx else None
            media = getattr(m, "media", None)
            msg_rows.append({
                "id": m.id,
                "created_at": _fmt_dt(m.created_at),
                "date": _fmt_dt(m.created_at, "%d %b %Y"),
                "time": _fmt_dt(m.created_at, "%I:%M:%S %p"),
                "direction": m.direction,
                "sender": "Donor" if m.direction == "in" else (conv.rm.rm_name if conv.rm else "RM"),
                "type": m.message_type,
                "body": _get_msg_body(m),
                "status": m.status,
                "media": {"url": media.file.url, "mime_type": media.mime_type, "size_kb": round(media.size / 1024, 1)} if media else None,
                "reply_to_id": m.reply_to_id,
                "reply_time_min": r_min,
                "gap_min": _minutes_between(prev.created_at, m.created_at) if prev else None,
            })

        conv_rows.append({
            "id": conv.id,
            "rm": {
                "rm_name": conv.rm.rm_name if conv.rm else "—",
                "rm_code": conv.rm.rm_code if conv.rm else "",
                "branch": conv.rm.get_rm_branch_display() if conv.rm and conv.rm.rm_branch else "—",
                "branch_code": conv.rm.rm_branch if conv.rm else "",
                "tl_name": conv.rm.tl_name or "—" if conv.rm else "—",
                "is_active": conv.rm.is_active if conv.rm else False,
                "wa_active": conv.rm.active_whatsapp if conv.rm else False,
            } if conv.rm else None,
            "status": conv.status or "open",
            "is_active": conv.is_active,
            "unread_count": conv.unread_count,
            "started_at": _fmt_dt(conv.created_at),
            "first_msg_time": _fmt_dt(first_m.created_at) if first_m else None,
            "last_msg_time": _fmt_dt(last_m.created_at) if last_m else None,
            "duration_min": _minutes_between(first_m.created_at, last_m.created_at) if first_m and last_m else None,
            "total_msgs": len(cmsgs),
            "in_count": in_count,
            "out_count": out_count,
            "reply_time_min": c_reply,
            "last_preview": conv.last_message_preview or "",
            "messages": msg_rows,
        })

        tot_in += in_count
        tot_out += out_count
        if first_m:
            first_contact = min(first_contact, first_m.created_at) if first_contact else first_m.created_at
        if last_m:
            last_contact = max(last_contact, last_m.created_at) if last_contact else last_m.created_at

        if conv.rm:
            agg = rm_agg.get(conv.rm.rm_code)
            if not agg:
                agg = rm_agg[conv.rm.rm_code] = dict(
                    rm_name=conv.rm.rm_name,
                    rm_code=conv.rm.rm_code,
                    branch=conv.rm.get_rm_branch_display() if conv.rm.rm_branch else "—",
                    branch_code=conv.rm.rm_branch or "",
                    tl_name=conv.rm.tl_name or "—",
                    is_active=conv.rm.is_active,
                    wa_active=conv.rm.active_whatsapp,
                    conv_count=0, total_msgs=0, in_count=0, out_count=0,
                    _first=None, _last=None, _replies=[],
                )
            agg["conv_count"] += 1
            agg["total_msgs"] += len(cmsgs)
            agg["in_count"] += in_count
            agg["out_count"] += out_count
            if first_m:
                agg["_first"] = min(agg["_first"], first_m.created_at) if agg["_first"] else first_m.created_at
            if last_m:
                agg["_last"] = max(agg["_last"], last_m.created_at) if agg["_last"] else last_m.created_at
            if c_reply is not None:
                agg["_replies"].append(c_reply)

    rm_rows = []
    for agg in rm_agg.values():
        replies = agg.pop("_replies")
        first_at = agg.pop("_first")
        last_at = agg.pop("_last")
        agg["first_chat_at"] = _fmt_dt(first_at, "%d %b %Y, %I:%M %p")
        agg["last_chat_at"] = _fmt_dt(last_at, "%d %b %Y, %I:%M %p")
        agg["avg_reply_min"] = round(sum(replies) / len(replies), 1) if replies else None
        rm_rows.append(agg)
    rm_rows.sort(key=lambda x: x["total_msgs"], reverse=True)

    conv_rows.reverse()

    blocks = BlockedContact.objects.filter(donor=donor).select_related("blocked_by").order_by("-blocked_at")
    block_rows = [{
        "is_active": b.is_active,
        "reason": b.reason or "-",
        "blocked_by": b.blocked_by.rm_name if b.blocked_by else "-",
        "blocked_at": _fmt_dt(b.blocked_at, "%d %b %Y, %I:%M %p"),
        "unblocked_at": _fmt_dt(b.unblocked_at, "%d %b %Y, %I:%M %p"),
        "unblocked_by": b.unblocked_by or "-",
        "wa_api_blocked": b.wa_api_blocked,
    } for b in blocks]

    return JsonResponse({
        "found": True,
        "query": q,
        "donor": {
            "phone": donor.phone_number,
            "phone_fmt": _pretty_phone(donor.phone_number),
            "wa_link": f"https://wa.me/{_digits_only(donor.phone_number)}",
            "name": "Unknown",
            "first_seen": _fmt_dt(donor.created_at, "%d %b %Y, %I:%M %p"),
            "is_blocked": any(b["is_active"] for b in block_rows),
        },
        "summary": {
            "rm_count": len(rm_rows),
            "conv_count": len(conv_rows),
            "total_msgs": tot_in + tot_out,
            "in_count": tot_in,
            "out_count": tot_out,
            "first_contact": _fmt_dt(first_contact, "%d %b %Y, %I:%M %p") or "-",
            "last_contact": _fmt_dt(last_contact, "%d %b %Y, %I:%M %p") or "-",
            "avg_reply_min": round(sum(reply_mins) / len(reply_mins), 1) if reply_mins else None,
            "truncated": len(msgs) >= DONOR_SEARCH_MSG_CAP,
        },
        "rms": rm_rows,
        "conversations": conv_rows,
        "blocks": block_rows,
    })
