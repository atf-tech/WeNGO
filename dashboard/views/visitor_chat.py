import json
from datetime import timedelta, datetime, date as date_type
from decimal import Decimal

from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import (
    Count, Sum, Min, Max, Avg, Q, F, Value, IntegerField, Case, When
)
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator

from dashboard.models import RM
from dashboard.views.auth import superuser_required
from RMPortal.models import (
    VisitorSession, VisitorConversation, VisitorMessage, VisitorPageView,
)


# ──────────────────────────────────────────────
# Period helpers
# ──────────────────────────────────────────────

def _parse_period(request):
    """Return (start_dt, end_dt) from request GET params.

    Accepts:
      ?period=today|yesterday|week|month|custom
      &from_date=YYYY-MM-DD&to_date=YYYY-MM-DD  (for custom)

    Defaults to today.
    """
    period = request.GET.get("period", "today").strip().lower()
    branch = request.GET.get("branch", "").strip()

    today = timezone.localtime(timezone.now()).date()

    if period == "yesterday":
        start = today - timedelta(days=1)
        end = start
    elif period == "week":
        start = today - timedelta(days=today.weekday())
        end = today
    elif period == "14days":
        start = today - timedelta(days=13)
        end = today
    elif period == "month":
        start = today.replace(day=1)
        end = today
    elif period == "custom":
        try:
            from_str = request.GET.get("from_date", "").strip()
            to_str = request.GET.get("to_date", "").strip()
            start = datetime.strptime(from_str, "%Y-%m-%d").date()
            end = datetime.strptime(to_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            start = today
            end = today
    else:
        start = today
        end = today

    start_dt = timezone.make_aware(
        datetime.combine(start, datetime.min.time()),
        timezone.get_current_timezone(),
    )
    end_dt = timezone.make_aware(
        datetime.combine(end, datetime.max.time()),
        timezone.get_current_timezone(),
    )

    return start_dt, end_dt, period, branch


def _branch_filter(branch):
    """Return a Q filter for RM.branch or none."""
    if branch:
        return Q(rm__rm_branch=branch)
    return Q()


def _response_time_qs(start_dt, end_dt, branch=""):
    qs = VisitorConversation.objects.filter(
        created_at__gte=start_dt,
        created_at__lte=end_dt,
        visitor_first_message_at__isnull=False,
        rm_first_response_at__isnull=False,
        rm_first_response_at__gte=F("visitor_first_message_at"),
        response_time_seconds__isnull=False,
    )
    if branch:
        qs = qs.filter(rm__rm_branch=branch)
    return qs


def _avg_response_minutes(qs):
    avg_resp = qs.aggregate(avg=Avg("response_time_seconds"))["avg"]
    return round(avg_resp / 60, 1) if avg_resp is not None else None


# ──────────────────────────────────────────────
# Entry view — renders KPI values server-side
# ──────────────────────────────────────────────

@superuser_required(login_url='/dashboard/login')
def visitor_chat(request):
    branches = RM.BRANCH_CHOICES
    today = timezone.localtime(timezone.now()).date()

    today_start = timezone.make_aware(
        datetime.combine(today, datetime.min.time()),
        timezone.get_current_timezone(),
    )
    today_end = timezone.make_aware(
        datetime.combine(today, datetime.max.time()),
        timezone.get_current_timezone(),
    )

    yesterday = today - timedelta(days=1)
    yesterday_start = timezone.make_aware(
        datetime.combine(yesterday, datetime.min.time()),
        timezone.get_current_timezone(),
    )

    week_start = today_start - timedelta(days=today.weekday())
    last_week_start = week_start - timedelta(days=7)
    month_start = today_start.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    def pct(current, previous):
        if previous:
            return round(((current - previous) / previous) * 100, 2)
        return 0.0

    # ── Visitors today ──
    visitors_today = VisitorSession.objects.filter(
        first_seen_at__gte=today_start, first_seen_at__lte=today_end
    ).count()
    visitors_yesterday = VisitorSession.objects.filter(
        first_seen_at__gte=yesterday_start, first_seen_at__lt=today_start
    ).count()

    # ── Visitors week / month ──
    visitors_week = VisitorSession.objects.filter(
        first_seen_at__gte=week_start, first_seen_at__lte=today_end
    ).count()
    prev_week = VisitorSession.objects.filter(
        first_seen_at__gte=last_week_start, first_seen_at__lt=week_start
    ).count()

    visitors_month = VisitorSession.objects.filter(
        first_seen_at__gte=month_start, first_seen_at__lte=today_end
    ).count()
    prev_month = VisitorSession.objects.filter(
        first_seen_at__gte=last_month_start, first_seen_at__lt=month_start
    ).count()

    # ── Conversations today ──
    conversations_today = VisitorConversation.objects.filter(
        created_at__gte=today_start, created_at__lte=today_end
    ).count()

    # ── Visitor Messages today ──
    visitor_msgs_today = VisitorMessage.objects.filter(
        direction="visitor",
        created_at__gte=today_start, created_at__lte=today_end,
    ).count()

    # ── RM Replies today ──
    rm_replies_today = VisitorMessage.objects.filter(
        direction="rm",
        created_at__gte=today_start, created_at__lte=today_end,
    ).count()

    # ── Reply Rate ──
    convs_with_reply = VisitorConversation.objects.filter(
        created_at__gte=today_start, created_at__lte=today_end,
        rm_first_response_at__isnull=False,
    ).count()
    reply_rate = round((convs_with_reply / conversations_today * 100)) if conversations_today else 0

    # ── Avg Response Time ──
    avg_resp_min = _avg_response_minutes(
        _response_time_qs(today_start, today_end)
    )
    avg_resp_label = (
        "Excellent" if avg_resp_min is not None and avg_resp_min < 5
        else "Good" if avg_resp_min is not None and avg_resp_min < 15
        else "Slow" if avg_resp_min is not None
        else "—"
    )

    # ── Return Visitors (today) ──
    return_visitors = VisitorSession.objects.filter(
        is_returning=True,
        first_seen_at__gte=today_start, first_seen_at__lte=today_end,
    ).count()

    device_data = VisitorSession.objects.filter(
        first_seen_at__gte=today_start, first_seen_at__lte=today_end,
    ).values("device_type").annotate(cnt=Count("id"))

    desktop_count = 0
    mobile_count = 0
    for d in device_data:
        if d["device_type"] == "desktop":
            desktop_count = d["cnt"]
        elif d["device_type"] in ("mobile", "tablet"):
            mobile_count += d["cnt"]

    avg_pages = VisitorSession.objects.filter(
        first_seen_at__gte=today_start, first_seen_at__lte=today_end,
    ).aggregate(avg=Avg("page_count"))["avg"] or 0

    # ── CRM widgets ──
    online_now = VisitorSession.objects.filter(
        is_online=True,
        last_seen_at__gte=today_start,
        last_seen_at__lte=today_end,
    ).count()

    status_agg = VisitorConversation.objects.filter(
        created_at__gte=today_start, created_at__lte=today_end,
    ).values("status").annotate(cnt=Count("id"))

    status_map = {s["status"]: s["cnt"] for s in status_agg}
    waiting = status_map.get("waiting", 0)
    active = status_map.get("active", 0)
    closed = status_map.get("closed", 0)
    missed = status_map.get("missed", 0)

    missed_agg = VisitorConversation.objects.filter(
        created_at__gte=today_start, created_at__lte=today_end,
        status="missed",
    ).values("missed_reason").annotate(cnt=Count("id"))
    missed_map = {m["missed_reason"]: m["cnt"] for m in missed_agg}
    quickly_left = missed_map.get("quickly_left", 0)
    night_chat = missed_map.get("night_chat", 0)

    context = {
        "branches": branches,
        # Card 1: Visitors (Today)
        "visitors_today": visitors_today,
        "visitors_today_pct": pct(visitors_today, visitors_yesterday),
        "visitors_yesterday": visitors_yesterday,
        # Card 2: Visitors This Week
        "visitors_week": visitors_week,
        "visitors_week_pct": pct(visitors_week, prev_week),
        # Card 3: Visitors This Month
        "visitors_month": visitors_month,
        "visitors_month_pct": pct(visitors_month, prev_month),
        # Card 4: Conversations (Today)
        "conversations_today": conversations_today,
        # Card 5: Visitor Messages
        "visitor_msgs_today": visitor_msgs_today,
        "rm_replies_today": rm_replies_today,
        # Card 6: Reply Rate
        "reply_rate": reply_rate,
        "convs_with_reply": convs_with_reply,
        "total_convs": conversations_today,
        # Card 7: Avg Response Time
        "avg_resp_min": avg_resp_min,  # None handled in template
        "avg_resp_label": avg_resp_label,
        # Card 8: Return Visitors
        "return_visitors": return_visitors,
        "desktop_count": desktop_count,
        "mobile_count": mobile_count,
        "avg_pages": round(avg_pages, 1),
        # CRM Widgets
        "online_now": online_now,
        "waiting": waiting,
        "active": active,
        "missed": missed,
        "quickly_left": quickly_left,
        "night_chat": night_chat,
    }

    return render(request, 'dashboard/visitor_chat.html', context)


# ──────────────────────────────────────────────
# 1. api/kpi/ — All KPI cards + polar data
# ──────────────────────────────────────────────

@superuser_required(login_url='/dashboard/login')
def api_kpi(request):
    start_dt, end_dt, period, branch = _parse_period(request)

    # ── Branch filter helper ──
    branch_filter = Q()
    if branch:
        branch_filter = Q(visitor__assigned_rm__rm_branch=branch)

    # ── Session helper (filtered by period + branch) ──
    def sessions_in_range(s, e):
        qs = VisitorSession.objects.filter(
            first_seen_at__gte=s, first_seen_at__lte=e
        )
        if branch:
            qs = qs.filter(assigned_rm__rm_branch=branch)
        return qs

    # ── Conversations in period (with optional branch) ──
    conv_qs = VisitorConversation.objects.filter(
        created_at__gte=start_dt, created_at__lte=end_dt
    )
    if branch:
        conv_qs = conv_qs.filter(visitor__assigned_rm__rm_branch=branch)

    # ── Messages in range (with optional branch) ──
    def msgs_in_range(s, e, direction):
        qs = VisitorMessage.objects.filter(
            direction=direction,
            created_at__gte=s, created_at__lte=e,
        )
        if branch:
            qs = qs.filter(conversation__visitor__assigned_rm__rm_branch=branch)
        return qs

    # ── Comparison period boundaries ──
    today = timezone.localtime(timezone.now()).date()
    today_start = timezone.make_aware(
        datetime.combine(today, datetime.min.time()),
        timezone.get_current_timezone(),
    )
    today_end = timezone.make_aware(
        datetime.combine(today, datetime.max.time()),
        timezone.get_current_timezone(),
    )

    yesterday = today - timedelta(days=1)
    yesterday_start = timezone.make_aware(
        datetime.combine(yesterday, datetime.min.time()),
        timezone.get_current_timezone(),
    )

    week_start = today_start - timedelta(days=today.weekday())
    last_week_start = week_start - timedelta(days=7)
    month_start = today_start.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    def pct_change(current, previous):
        if previous:
            return round(((current - previous) / previous) * 100, 2)
        return 0.0

    # ── Main KPI values (ALL respect selected period) ──
    visitors_in_period = sessions_in_range(start_dt, end_dt).count()
    visitors_yesterday = sessions_in_range(yesterday_start, today_start).count()
    visitors_week = sessions_in_range(week_start, end_dt).count()
    visitors_month = sessions_in_range(month_start, end_dt).count()

    # Comparison counts
    prev_week_count = sessions_in_range(last_week_start, week_start).count()
    prev_month_count = sessions_in_range(last_month_start, month_start).count()

    # Conversations
    total_convs = conv_qs.count()

    # Messages (in period)
    visitor_msgs = msgs_in_range(start_dt, end_dt, "visitor").count()
    rm_msgs = msgs_in_range(start_dt, end_dt, "rm").count()

    # Reply Rate
    convs_with_reply = conv_qs.filter(
        rm_first_response_at__isnull=False
    ).count()
    reply_rate = round((convs_with_reply / total_convs * 100)) if total_convs else 0

    # Avg Response Time
    avg_resp_min = _avg_response_minutes(
        _response_time_qs(start_dt, end_dt, branch)
    )

    # Return Visitors (in period)
    return_in_period = sessions_in_range(start_dt, end_dt).filter(
        is_returning=True
    ).count()

    # Device breakdown (in period)
    device_data = sessions_in_range(start_dt, end_dt).values(
        "device_type"
    ).annotate(cnt=Count("id"))

    desktop_count = 0
    mobile_count = 0
    for d in device_data:
        if d["device_type"] == "desktop":
            desktop_count = d["cnt"]
        elif d["device_type"] in ("mobile", "tablet"):
            mobile_count += d["cnt"]

    avg_pages = sessions_in_range(start_dt, end_dt).aggregate(
        avg=Avg("page_count")
    )["avg"] or 0

    # ── CRM Widgets (live/period) ──
    online_now = VisitorSession.objects.filter(
        is_online=True,
        last_seen_at__gte=start_dt,
        last_seen_at__lte=end_dt,
    )

    if branch:
        online_now = online_now.filter(
            assigned_rm__rm_branch=branch
        )

    online_now = online_now.count()

    # Status distribution in period
    status_agg = conv_qs.values("status").annotate(cnt=Count("id"))
    status_map = {s["status"]: s["cnt"] for s in status_agg}

    waiting = status_map.get("waiting", 0)
    active = status_map.get("active", 0)
    closed = status_map.get("closed", 0)
    missed = status_map.get("missed", 0)

    # Missed sub-types
    missed_agg = conv_qs.filter(status="missed").values("missed_reason").annotate(
        cnt=Count("id")
    )
    missed_map = {m["missed_reason"]: m["cnt"] for m in missed_agg}

    quickly_left = missed_map.get("quickly_left", 0)
    night_chat = missed_map.get("night_chat", 0)

    # ── Polar Chart Data ──
    polar_series = [waiting, active, closed, missed, quickly_left, night_chat]
    polar_labels = ["Waiting", "Active", "Closed", "Missed", "Quickly Left", "Night Chat"]



    return JsonResponse({
        "kpi": {
            "visitors_today": visitors_in_period,
            "visitors_today_pct": pct_change(visitors_in_period, visitors_yesterday),
            "visitors_yesterday": visitors_yesterday,
            "visitors_week": visitors_week,
            "visitors_week_pct": pct_change(visitors_week, prev_week_count),
            "visitors_month": visitors_month,
            "visitors_month_pct": pct_change(visitors_month, prev_month_count),
            "conversations_today": total_convs,
            "conversations_total": total_convs,
            "visitor_msgs_today": visitor_msgs,
            "rm_msgs_today": rm_msgs,
            "reply_rate": reply_rate,   
            "convs_with_reply": convs_with_reply,
            "total_convs": total_convs,
            "avg_resp_min": avg_resp_min,
            "avg_resp_label": "Excellent" if avg_resp_min is not None and avg_resp_min < 5 else "Good" if avg_resp_min is not None and avg_resp_min < 15 else "Slow" if avg_resp_min is not None else "—",
            "return_visitors": return_in_period,
            "desktop_count": desktop_count,
            "mobile_count": mobile_count,
            "avg_pages": round(avg_pages, 1),
        },
        "crm": {
            "online_now": online_now,
            "waiting": waiting,
            "active": active,
            "missed": missed,
            "quickly_left": quickly_left,
            "night_chat": night_chat,
        },
        "polar": {
            "series": polar_series,
            "labels": polar_labels,
        },
    })


# ──────────────────────────────────────────────
# 2. api/table/ — RM Leaderboard
# ──────────────────────────────────────────────

@superuser_required(login_url='/dashboard/login')
def api_table(request):
    start_dt, end_dt, period, branch = _parse_period(request)

    # Base RM queryset
    rms = RM.objects.filter(is_active=True)
    if branch:
        rms = rms.filter(rm_branch=branch)

    rows = []

    for rm in rms:
        convos = VisitorConversation.objects.filter(
            rm=rm,
            created_at__gte=start_dt,
            created_at__lte=end_dt,
        )

        conv_count = convos.count()
        if conv_count == 0:
            continue

        # Chat status breakdown
        status_agg = convos.values("status").annotate(cnt=Count("id"))
        status_map = {s["status"]: s["cnt"] for s in status_agg}

        # Missed reasons
        missed_agg = convos.filter(status="missed").values("missed_reason").annotate(cnt=Count("id"))
        missed_map = {m["missed_reason"]: m["cnt"] for m in missed_agg}

        # Messages
        visitor_msg_count = VisitorMessage.objects.filter(
            conversation__in=convos, direction="visitor"
        ).count()
        rm_msg_count = VisitorMessage.objects.filter(
            conversation__in=convos, direction="rm"
        ).count()

        # Visitors (distinct)
        visitor_count = convos.values("visitor").distinct().count()

        # Avg response time
        avg_resp = convos.filter(
            response_time_seconds__isnull=False
        ).aggregate(avg=Avg("response_time_seconds"))["avg"]
        avg_resp_min = round(avg_resp / 60, 1) if avg_resp else None

        # Reply rate
        replied = convos.filter(rm_first_response_at__isnull=False).count()
        reply_pct = round((replied / conv_count * 100)) if conv_count else 0

        # Last active
        last_active = convos.aggregate(
            last=Max("last_message_at")
        )["last"]
        last_active_str = ""
        if last_active:
            last_active_local = timezone.localtime(last_active)
            last_active_str = last_active_local.strftime("%d %b %I:%M %p")

        rows.append({
            "rm_name": rm.rm_name,
            "rm_code": rm.rm_code,
            "rm_branch": rm.get_rm_branch_display() if rm.rm_branch else "—",
            "rm_branch_code": rm.rm_branch or "",
            "active_chat": rm.active_visitor_chat,
            "visitors": visitor_count,
            "conversations": conv_count,
            "visitor_msgs": visitor_msg_count,
            "rm_msgs": rm_msg_count,
            "reply_rate": reply_pct,
            "avg_resp_min": avg_resp_min,
            "waiting": status_map.get("waiting", 0),
            "active": status_map.get("active", 0),
            "closed": status_map.get("closed", 0),
            "missed": status_map.get("missed", 0),
            "quickly_left": missed_map.get("quickly_left", 0),
            "night_chat": missed_map.get("night_chat", 0),
            "last_active": last_active_str,
        })

    # Sort by conversations descending, assign ranks
    rows.sort(key=lambda r: (-r["conversations"], -r["reply_rate"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1

    return JsonResponse({"rows": rows})


# ──────────────────────────────────────────────
# 3. api/visitors/ — Paginated visitor details
# ──────────────────────────────────────────────

@superuser_required(login_url='/dashboard/login')
def api_visitors(request):
    start_dt, end_dt, period, branch = _parse_period(request)
    page = request.GET.get("page", 1)
    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1

    qs = VisitorSession.objects.filter(
        first_seen_at__gte=start_dt, first_seen_at__lte=end_dt
    ).select_related("assigned_rm").order_by("-first_seen_at")

    if branch:
        qs = qs.filter(assigned_rm__rm_branch=branch)

    paginator = Paginator(qs, 50)
    try:
        visitors_page = paginator.page(page)
    except Exception:
        return JsonResponse({"rows": [], "page": 1, "total": 0, "total_pages": 0, "per_page": 50})

    rows = []
    for v in visitors_page.object_list:
        # Get conversation info for this visitor
        conv = VisitorConversation.objects.filter(visitor=v).order_by("-created_at").first()
        chat_status = conv.status if conv else "no_chat"
        missed_reason = conv.missed_reason if conv else None

        # Time spent display
        time_spent = ""
        time_seconds = 0
        if v.total_time_seconds:
            time_seconds = v.total_time_seconds
            mins = time_seconds // 60
            secs = time_seconds % 60
            time_spent = f"{mins}m {secs}s"

        # Response time for visitor
        response_time_display = "—"
        if conv and conv.response_time_seconds:
            mins = conv.response_time_seconds // 60
            secs = conv.response_time_seconds % 60
            response_time_display = f"{mins}m {secs}s"

        rows.append({
            "name": v.name or "—",
            "email": v.email or "—",
            "phone": v.phone or "—",
            "city": v.city or "—",
            "device": v.device_type or "—",
            "browser": v.browser or "—",
            "pages": v.page_count or 0,
            "time_spent": time_spent,
            "time_spent_seconds": time_seconds,
            "is_online": v.is_online,
            "chat_status": chat_status,
            "missed_reason": missed_reason,
            "response_time": response_time_display,
            "assigned_rm": v.assigned_rm.rm_name if v.assigned_rm else "—",
            "referrer": v.referrer or "—",
            "first_seen": timezone.localtime(v.first_seen_at).strftime("%d %b %I:%M %p") if v.first_seen_at else "—",
            "last_seen": timezone.localtime(v.last_seen_at).strftime("%d %b %I:%M %p") if v.last_seen_at else "—",
        })

    return JsonResponse({
        "rows": rows,
        "page": visitors_page.number,
        "total": paginator.count,
        "total_pages": paginator.num_pages,
        "per_page": 50,
    })


# ──────────────────────────────────────────────
# 4. api/charts/ — Overview + Branch + Response
# ──────────────────────────────────────────────

@superuser_required(login_url='/dashboard/login')
def api_charts(request):
    # Global period remains for branch + response data only.
    start_dt, end_dt, period, branch = _parse_period(request)

    chart_agg = request.GET.get("chart", "daily")

    today = timezone.localtime(timezone.now()).date()
    today_start = timezone.make_aware(
        datetime.combine(today, datetime.min.time()),
        timezone.get_current_timezone(),
    )
    today_end = timezone.make_aware(
        datetime.combine(today, datetime.max.time()),
        timezone.get_current_timezone(),
    )

    if chart_agg == "daily":
        chart_start_dt = today_start - timedelta(days=13)
        chart_end_dt = today_end
    elif chart_agg == "weekly":
        chart_start_dt = today_start.replace(day=1)
        chart_end_dt = today_end
    else:
        chart_start_dt = today_start.replace(day=1)
        chart_end_dt = today_end

    chart_start_date = chart_start_dt.date()
    chart_end_date = chart_end_dt.date()

    # ── Overview Chart (Line/Bar/Area) ──
    overview_categories = []
    overview_conversations = []
    overview_messages = []
    overview_visitors = []

    if chart_agg == "daily":
        cur = chart_start_dt
        while cur <= chart_end_dt:
            day_end = cur + timedelta(days=1)
            label = cur.strftime("%d %b")
            overview_categories.append(label)

            conv_qs = VisitorConversation.objects.filter(
                created_at__gte=cur,
                created_at__lt=day_end
            )
            if branch:
                conv_qs = conv_qs.filter(
                    visitor__assigned_rm__rm_branch=branch
                )
            conv_count = conv_qs.count()

            msg_qs = VisitorMessage.objects.filter(
                created_at__gte=cur,
                created_at__lt=day_end
            )
            if branch:
                msg_qs = msg_qs.filter(
                    conversation__visitor__assigned_rm__rm_branch=branch
                )
            msg_count = msg_qs.count()

            visitor_qs = VisitorSession.objects.filter(
                first_seen_at__gte=cur,
                first_seen_at__lt=day_end
            )
            if branch:
                visitor_qs = visitor_qs.filter(
                    assigned_rm__rm_branch=branch
                )
            vis_count = visitor_qs.count()

            overview_conversations.append(conv_count)
            overview_messages.append(msg_count)
            overview_visitors.append(vis_count)
            cur = day_end
    elif chart_agg == "weekly":
        cur = chart_start_dt
        while cur <= chart_end_dt:
            period_end = min(cur + timedelta(days=7), chart_end_dt + timedelta(days=1))
            label = cur.strftime("%d %b")
            overview_categories.append(label)

            conv_qs = VisitorConversation.objects.filter(
                created_at__gte=cur,
                created_at__lt=period_end
            )
            if branch:
                conv_qs = conv_qs.filter(
                    visitor__assigned_rm__rm_branch=branch
                )
            conv_count = conv_qs.count()

            msg_qs = VisitorMessage.objects.filter(
                created_at__gte=cur,
                created_at__lt=period_end
            )
            if branch:
                msg_qs = msg_qs.filter(
                    conversation__visitor__assigned_rm__rm_branch=branch
                )
            msg_count = msg_qs.count()

            visitor_qs = VisitorSession.objects.filter(
                first_seen_at__gte=cur,
                first_seen_at__lt=period_end
            )
            if branch:
                visitor_qs = visitor_qs.filter(
                    assigned_rm__rm_branch=branch
                )
            vis_count = visitor_qs.count()

            overview_conversations.append(conv_count)
            overview_messages.append(msg_count)
            overview_visitors.append(vis_count)

            cur = period_end
    else:
        cur = chart_start_dt
        while cur <= chart_end_dt:
            day_end = cur + timedelta(days=1)
            label = cur.strftime("%d %b")
            overview_categories.append(label)

            conv_qs = VisitorConversation.objects.filter(
                created_at__gte=cur,
                created_at__lt=day_end
            )
            if branch:
                conv_qs = conv_qs.filter(
                    visitor__assigned_rm__rm_branch=branch
                )
            conv_count = conv_qs.count()

            msg_qs = VisitorMessage.objects.filter(
                created_at__gte=cur,
                created_at__lt=day_end
            )
            if branch:
                msg_qs = msg_qs.filter(
                    conversation__visitor__assigned_rm__rm_branch=branch
                )
            msg_count = msg_qs.count()

            visitor_qs = VisitorSession.objects.filter(
                first_seen_at__gte=cur,
                first_seen_at__lt=day_end
            )
            if branch:
                visitor_qs = visitor_qs.filter(
                    assigned_rm__rm_branch=branch
                )
            vis_count = visitor_qs.count()

            overview_conversations.append(conv_count)
            overview_messages.append(msg_count)
            overview_visitors.append(vis_count)
            cur = day_end

    # ── Branch-wise Bar Chart ──
    branch_choice_labels = dict(RM.BRANCH_CHOICES)

    def branch_label(branch_code):
        return branch_choice_labels.get(
            branch_code,
            (branch_code or "").replace("_", " ").replace("-", " ").title(),
        )

    if branch:
        branch_codes = [branch]
    else:
        branch_codes = list(
            RM.objects.exclude(rm_branch__isnull=True)
            .exclude(rm_branch="")
            .order_by("rm_branch")
            .values_list("rm_branch", flat=True)
            .distinct()
        )

    branch_categories = []
    leads_data = []
    received_data = []
    sent_data = []
    conv_pct_data = []
    branch_data = []

    for branch_code in branch_codes:
        b_convos = VisitorConversation.objects.filter(
            rm__rm_branch=branch_code,
            created_at__gte=start_dt,
            created_at__lte=end_dt,
        )

        b_conv_count = b_convos.count()
        b_visitor_count = b_convos.values("visitor").distinct().count()
        b_msg_in = VisitorMessage.objects.filter(
            conversation__in=b_convos,
            direction="visitor",
        ).count()
        b_msg_out = VisitorMessage.objects.filter(
            conversation__in=b_convos,
            direction="rm",
        ).count()
        b_replied = b_convos.filter(rm_first_response_at__isnull=False).count()
        b_conv_pct = round((b_replied / b_conv_count * 100)) if b_conv_count else 0

        branch_categories.append(branch_label(branch_code))
        leads_data.append(b_visitor_count)
        received_data.append(b_msg_in)
        sent_data.append(b_msg_out)
        conv_pct_data.append(b_conv_pct)
        branch_data.append({
            "leads": b_visitor_count,
            "received": b_msg_in,
            "sent": b_msg_out,
            "conv_pct": b_conv_pct,
        })

    branch_series = [
        {"name": "Leads", "data": leads_data},
        {"name": "Received", "data": received_data},
        {"name": "Sent", "data": sent_data},
        {"name": "Conv %", "data": conv_pct_data},
    ]

    # ── Response Time per RM Chart ──
    resp_rm_names = []
    resp_times = []

    rm_response_rows = (
        _response_time_qs(start_dt, end_dt, branch)
        .values("rm_id", "rm__rm_name")
        .annotate(avg_resp=Avg("response_time_seconds"))
        .order_by("rm__rm_name")[:10]
    )

    for rm in rm_response_rows:
        avg_min = round(rm["avg_resp"] / 60, 1) if rm["avg_resp"] is not None else 0
        resp_rm_names.append(rm["rm__rm_name"])
        resp_times.append(avg_min)

    return JsonResponse({
        "overview": {
            "categories": overview_categories,
            "conversations": overview_conversations,
            "messages": overview_messages,
            "visitors": overview_visitors,
        },
        "branch": {
            "categories": branch_categories,
            "series": branch_series,
            "labels": branch_categories,
            "data": branch_data,
        },
        "response": {
            "categories": resp_rm_names,
            "data": resp_times,
            "rm_names": resp_rm_names,
            "times": resp_times,
        },
    })
