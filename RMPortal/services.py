import requests
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import RM


def _wa_headers(access_token=None):
    token = access_token or settings.WA_ACCESS_TOKEN
    return {"Authorization": f"Bearer {token}"}


def _post_to_meta(url, payload, timeout=10, files=None, access_token=None):
    """
    Call the WhatsApp Cloud API and surface the actual error body on failure.
    Meta returns useful JSON like
        {"error":{"message":"...","type":"OAuthException","code":190,...}}
    which the default raise_for_status() throws away. We log it and re-raise
    so the caller can decide what to do.
    """
    headers = _wa_headers(access_token)
    if files is not None:
        res = requests.post(url, headers=headers, files=files, timeout=timeout)
    else:
        res = requests.post(url, headers=headers, json=payload, timeout=timeout)

    if res.status_code >= 400:
        # Don't trust .json() — Meta sometimes returns HTML on auth failures.
        try:
            err_body = res.json()
        except Exception:
            err_body = res.text[:500]
        print(
            "WhatsApp API ERROR ->",
            "status", res.status_code,
            "url", url,
            "payload", payload,
            "response", err_body,
        )
        # Re-raise so the caller still knows the call failed.
        res.raise_for_status()

    return res.json()


def send_whatsapp_message(to, text, phone_number_id=None, access_token=None):
    pid = phone_number_id or settings.WA_PHONE_NUMBER_ID
    url = f"https://graph.facebook.com/v21.0/{pid}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    return _post_to_meta(url, payload, timeout=10, access_token=access_token)


def mark_whatsapp_message_as_read(message_id, phone_number_id=None, access_token=None):
    """
    Tell WhatsApp that this message has been read by business.
    Triggers blue ticks on donor side. Best-effort — failures are logged but
    never propagate (don't want to break the chat-open flow).
    """
    pid = phone_number_id or settings.WA_PHONE_NUMBER_ID
    url = f"https://graph.facebook.com/v21.0/{pid}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    try:
        _post_to_meta(url, payload, timeout=5, access_token=access_token)
    except Exception as e:
        print("WhatsApp mark-as-read failed:", e)


# Media Support (All Types)

def upload_media_to_whatsapp(file_path, mime_type, phone_number_id=None, access_token=None):
    pid = phone_number_id or settings.WA_PHONE_NUMBER_ID
    url = f"https://graph.facebook.com/v21.0/{pid}/media"
    with open(file_path, "rb") as f:
        files = {
            "file": (file_path, f, mime_type),
            "messaging_product": (None, "whatsapp"),
        }
        return _post_to_meta(url, payload=None, timeout=20, files=files, access_token=access_token)["id"]


def send_whatsapp_media_message(to, media_id, media_type, caption=None, phone_number_id=None, access_token=None):
    pid = phone_number_id or settings.WA_PHONE_NUMBER_ID
    url = f"https://graph.facebook.com/v21.0/{pid}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": media_type,
    }

    if media_type == "audio":
        payload["audio"] = {"id": media_id, "voice": True}
    else:
        payload[media_type] = {"id": media_id}
        if caption and media_type in ["image", "video", "document"]:
            payload[media_type]["caption"] = caption

    return _post_to_meta(url, payload, timeout=10, access_token=access_token)



def _dedicated_branches():
    """
    Return branches that have their own unique WA phone_number_id.
    These RMs must only receive messages from their dedicated number —
    never from the shared main number.
    """
    from collections import Counter
    counts = Counter(creds["phone_number_id"] for creds in settings.WA_NUMBERS.values())
    return [b for b, creds in settings.WA_NUMBERS.items() if counts[creds["phone_number_id"]] == 1]


def assign_rm(branch=None):
    """
    FCFS round-robin for WhatsApp messages.
    Both whatsapp_permission (admin grant) AND active_whatsapp (RM online
    toggle) must be True. last_assigned_at is stamped when the RM goes
    online, so the RM who came online earliest gets the first message.
    If branch is provided, only RMs from that branch are considered.
    If branch is None (main number), dedicated-branch RMs are excluded
    so they only ever receive messages from their own number.
    """
    with transaction.atomic():
        qs = (
            RM.objects
            .select_for_update(skip_locked=True)
            .filter(is_active=True, whatsapp_permission=True, active_whatsapp=True)
        )
        if branch:
            qs = qs.filter(rm_branch=branch)
        else:
            dedicated = _dedicated_branches()
            if dedicated:
                qs = qs.exclude(rm_branch__in=dedicated)

        rm = qs.order_by(F("last_assigned_at").asc(nulls_last=True)).first()

        if not rm:
            return None

        rm.last_assigned_at = timezone.now()
        rm.save(update_fields=["last_assigned_at"])

        return rm
    
    


# Visitor Live Chat Services

WAITING_EXPIRY_MINUTES = 30


def expire_stale_waiting_conversations(max_age_minutes=WAITING_EXPIRY_MINUTES):
    """
    Spec §9 — flip any `waiting` VisitorConversation older than
    `max_age_minutes` with no RM reply to `missed`. Reason is set per row:
      - rm_no_reply    — visitor had typed at least once
      - stale_waiting  — visitor never typed

    Also flips every RM offline during night hours (spec §5, safety net).

    Called opportunistically when an RM loads their inbox and from the
    background sweep thread.
    """
    from datetime import timedelta
    from .models import VisitorConversation
    from .utils import is_night_hours

    if is_night_hours():
        try:
            force_all_rms_offline()
        except Exception as e:
            print("force_all_rms_offline error:", e)

    now = timezone.now()
    cutoff = now - timedelta(minutes=max_age_minutes)

    stale = VisitorConversation.objects.filter(
        status="waiting",
        created_at__lt=cutoff,
        rm_first_response_at__isnull=True,
    ).only("id", "visitor_first_message_at")

    count = 0
    for convo in stale:
        reason = "rm_no_reply" if convo.visitor_first_message_at else "stale_waiting"
        VisitorConversation.objects.filter(id=convo.id).update(
            status="missed",
            missed_reason=reason,
            closed_at=now,
        )
        count += 1
    return count


def assign_rm_for_visitor(exclude_ids=None):
    """
    Round-robin RM assignment for visitor live chat.
    Only RMs with is_active=True AND active_visitor_chat=True are eligible.
    Thread-safe via select_for_update.

    `exclude_ids` — iterable of RM ids to skip (used by the 30-s slow-response
    chain so we don't retry the same RM we just gave up on).

    Night-hours hard gate (spec §5): never returns an RM between 12:00 AM
    and 9:30 AM IST, even if an RM's active_visitor_chat=True is still set.
    """
    from .utils import is_night_hours
    if is_night_hours():
        return None

    with transaction.atomic():
        qs = (
            RM.objects
            .select_for_update(skip_locked=True)
            .filter(is_active=True, active_visitor_chat=True)
        )
        if exclude_ids:
            qs = qs.exclude(id__in=list(exclude_ids))
        rm = qs.order_by(F("last_visitor_assigned_at").asc(nulls_last=True)).first()
        if not rm:
            return None
        rm.last_visitor_assigned_at = timezone.now()
        rm.save(update_fields=["last_visitor_assigned_at"])
        return rm


def force_all_rms_offline():
    """
    Spec §5 / §10 — flip every online RM offline and reassign any waiting
    visitors. Used by the background thread during night hours and as a
    safety net when the heartbeat sweep finds an RM is gone.
    """
    online = list(
        RM.objects.filter(active_visitor_chat=True, is_active=True)
    )
    for rm in online:
        rm.active_visitor_chat = False
        rm.save(update_fields=["active_visitor_chat"])
        try:
            reassign_rm_conversations(rm)
        except Exception as e:
            print("force_all_rms_offline reassign error:", e)


def pick_rm_for_visitor(visitor):
    """
    Sticky round-robin for a returning visitor.
    1. If visitor already has an assigned_rm that is still online → reuse it.
    2. Else pick the next online RM via round-robin.
    3. Else return None (caller should trigger offline fallback).
    """
    old_rm = visitor.assigned_rm if visitor else None
    if old_rm and old_rm.is_active and old_rm.active_visitor_chat:
        return old_rm
    return assign_rm_for_visitor()


def build_fallback_payload():
    """
    Single greeting bubble shown when all RMs are offline.
    Returned from session_init (HTTP) and pushed via WebSocket.
    """
    from django.conf import settings
    return {"greeting": settings.WA_FALLBACK_GREETING}


def send_visitor_fallback_message(convo):
    """
    Push the offline greeting to the visitor's widget as a normal agent
    message bubble when all RMs are offline.

    Spec §3 / §14 — one-time per conversation. Idempotent: checks and sets
    `convo.fallback_sent` so the greeting is never sent twice.
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from django.conf import settings

    if getattr(convo, "fallback_sent", False):
        return None

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"visitor_{convo.visitor.session_key}",
        {
            "type": "visitor_rm_message",
            "message": {
                "id": None,
                "body": settings.WA_FALLBACK_GREETING,
                "sender": "rm",
                "rm_name": "IPF",
            },
        },
    )

    try:
        convo.fallback_sent = True
        convo.save(update_fields=["fallback_sent"])
    except Exception as e:
        print("fallback_sent save failed:", e)

    return None


def _url_quote(text):
    from urllib.parse import quote
    return quote(text or "", safe="")


def assign_or_fallback(visitor):
    """
    Single entry point used by views/consumers when a visitor needs an RM.
    Returns a tuple (rm_or_none, convo). Ensures there's always a
    VisitorConversation row so the widget has somewhere to write messages.
    """
    from .models import VisitorConversation

    rm = pick_rm_for_visitor(visitor)

    convo = (
        VisitorConversation.objects
        .filter(visitor=visitor, status__in=["waiting", "active", "missed"])
        .order_by("-created_at")
        .first()
    )

    if rm:
        if convo:
            if convo.rm_id != rm.id or convo.status == "missed":
                convo.rm = rm
                convo.status = "waiting"
                convo.save(update_fields=["rm", "status"])
        else:
            convo = VisitorConversation.objects.create(
                visitor=visitor, rm=rm, status="waiting"
            )
        if visitor.assigned_rm_id != rm.id:
            visitor.assigned_rm = rm
            visitor.save(update_fields=["assigned_rm"])
        return rm, convo

    # No RM online → fallback
    if not convo:
        convo = VisitorConversation.objects.create(
            visitor=visitor, rm=None, status="missed"
        )
    send_visitor_fallback_message(convo)
    return None, convo


def reassign_convo_to_new_rm(old_convo, new_rm):
    """
    Hand off a single visitor conversation from its current RM to `new_rm`.
    - Marks old convo status='reassigned' (stays visible in old RM's list so
      the RM knows why the visitor went away).
    - Creates a fresh VisitorConversation under `new_rm` (status='waiting').
    - Pushes a `visitor_removed` to the old RM's inbox and a
      `visitor_new_session` to the new RM's inbox so both sides update live.

    Returns the newly-created conversation.
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from .models import VisitorConversation

    old_rm_id = old_convo.rm_id
    visitor = old_convo.visitor

    old_convo.status = "reassigned"
    old_convo.save(update_fields=["status"])

    new_convo = VisitorConversation.objects.create(
        visitor=visitor, rm=new_rm, status="waiting",
    )
    visitor.assigned_rm = new_rm
    visitor.save(update_fields=["assigned_rm"])

    channel_layer = get_channel_layer()
    if old_rm_id:
        try:
            async_to_sync(channel_layer.group_send)(
                f"visitor_inbox_rm_{old_rm_id}",
                {"type": "visitor_removed", "conversation_id": old_convo.id},
            )
        except Exception as e:
            print("reassign_convo_to_new_rm old-rm notify failed:", e)
    try:
        async_to_sync(channel_layer.group_send)(
            f"visitor_inbox_rm_{new_rm.id}",
            {
                "type": "visitor_new_session",
                "session_key": visitor.session_key,
                "conversation_id": new_convo.id,
                "visitor_name": visitor.name or visitor.email or visitor.ip_address,
                "ip": visitor.ip_address,
                "country": visitor.country,
                "city": visitor.city,
                "device_type": visitor.device_type,
                "current_page": visitor.current_page or "",
                "is_returning": visitor.is_returning,
            },
        )
    except Exception as e:
        print("reassign_convo_to_new_rm new-rm notify failed:", e)
    return new_convo


def reassign_rm_conversations(rm):
    """
    When RM goes offline, reassign only ONLINE visitors to the next RM.
    Offline visitors stay with this RM (conversation closed) — no need
    to hand off someone who already left.
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from django.utils import timezone
    from datetime import timedelta
    from .models import VisitorConversation

    channel_layer = get_channel_layer()
    online_cutoff = timezone.now() - timedelta(minutes=2)

    open_convos = VisitorConversation.objects.filter(
        rm=rm, status__in=["waiting", "active"]
    ).select_related("visitor")

    for convo in open_convos:
        visitor = convo.visitor
        visitor_is_online = (
            visitor.is_online
            and visitor.last_seen_at
            and visitor.last_seen_at >= online_cutoff
        )

        # If RM already sent their first message, the chat is active —
        # keep it pinned to this RM even when they go offline.
        rm_already_responded = convo.rm_first_response_at is not None
        if visitor_is_online and not rm_already_responded:
            # Online visitor, RM never responded (still waiting) — reassign
            new_rm = assign_rm_for_visitor()

            convo.status = "reassigned"
            convo.save(update_fields=["status"])

            # Tell old RM to remove the card
            async_to_sync(channel_layer.group_send)(
                f"visitor_inbox_rm_{rm.id}",
                {
                    "type": "visitor_removed",
                    "conversation_id": convo.id,
                }
            )

            if not new_rm:
                # No other RM online — push visitor to WhatsApp fallback
                fresh_convo = VisitorConversation.objects.create(
                    visitor=visitor, rm=None, status="missed"
                )
                visitor.assigned_rm = None
                visitor.save(update_fields=["assigned_rm"])
                send_visitor_fallback_message(fresh_convo)
                continue

            new_convo = VisitorConversation.objects.create(
                visitor=visitor,
                rm=new_rm,
                status="waiting",
            )
            visitor.assigned_rm = new_rm
            visitor.save(update_fields=["assigned_rm"])

            async_to_sync(channel_layer.group_send)(
                f"visitor_inbox_rm_{new_rm.id}",
                {
                    "type": "visitor_new_session",
                    "session_key": visitor.session_key,
                    "conversation_id": new_convo.id,
                    "visitor_name": visitor.name or visitor.email or visitor.ip_address,
                    "ip": visitor.ip_address,
                    "country": visitor.country,
                    "city": visitor.city,
                    "device_type": visitor.device_type,
                    "current_page": "",
                    "is_returning": False,
                }
            )
        else:
            # Offline visitor — do nothing, keep conversation as-is
            # When RM comes back online, this chat will still be in their list
            pass


def get_visitor_geo(ip_address):
    """
    Fetch approximate geo info for an IP using ip-api.com (free, no key needed).
    Returns dict with country, region, city, isp — or empty dict on failure.
    """
    if not ip_address or ip_address in ("127.0.0.1", "::1"):
        return {}
    try:
        res = requests.get(
            f"http://ip-api.com/json/{ip_address}?fields=status,country,regionName,city,isp",
            timeout=3
        )
        data = res.json()
        if data.get("status") == "success":
            return {
                "country": data.get("country"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "isp": data.get("isp"),
            }
    except Exception:
        pass
    return {}


def parse_user_agent(ua_string):
    """
    Parse User-Agent string into browser, OS, and device_type.
    Returns dict with keys: browser, os, device_type.
    """
    if not ua_string:
        return {"browser": "Unknown", "os": "Unknown", "device_type": "unknown"}

    ua = ua_string.lower()

    if any(x in ua for x in ["iphone", "android", "mobile", "windows phone", "blackberry"]):
        device_type = "mobile"
    elif any(x in ua for x in ["ipad", "tablet"]):
        device_type = "tablet"
    else:
        device_type = "desktop"

    if "edg/" in ua or "edghtml" in ua:
        browser = "Edge"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    elif "chrome/" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "firefox/" in ua:
        browser = "Firefox"
    elif "safari/" in ua and "chrome" not in ua:
        browser = "Safari"
    else:
        browser = "Other"

    if "windows" in ua:
        os_name = "Windows"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "mac os" in ua:
        os_name = "macOS"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Other"

    return {"browser": browser, "os": os_name, "device_type": device_type}


def send_whatsapp_template(to, template_name, phone_number_id=None, access_token=None):
    pid = phone_number_id or settings.WA_PHONE_NUMBER_ID
    url = f"https://graph.facebook.com/v21.0/{pid}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
        },
    }
    return _post_to_meta(url, payload, timeout=10, access_token=access_token)