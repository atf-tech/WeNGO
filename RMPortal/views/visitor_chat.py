import uuid

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from dashboard.models import *
from dashboard.models import RM
from RMPortal.models import (
    VisitorSession, VisitorConversation, VisitorMessage, VisitorPageView,
)
from RMPortal.services import (
    assign_rm_for_visitor,
    get_visitor_geo,
    parse_user_agent,
)
from RMPortal.utils import is_night_hours

from .auth import rm_login_required
from .helpers import _get_client_ip


@csrf_exempt
def visitor_session_init(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
    except Exception:
        body = {}

    cookie_id = body.get("cookie_id") or request.COOKIES.get("vcid")

    if cookie_id:
        active_convo = (
            VisitorConversation.objects
            .filter(visitor__cookie_id=cookie_id, status__in=["waiting", "active"])
            .select_related("visitor", "rm")
            .order_by("-created_at")
            .first()
        )
        if active_convo:
            visitor = active_convo.visitor
            visitor.is_online = True
            visitor.save(update_fields=["is_online"])

            # Re-check: if the glued RM is no longer online, hand off now
            # (sticky → round-robin → WhatsApp fallback).
            current_rm = active_convo.rm
            rm_is_online = bool(
                current_rm
                and current_rm.is_active
                and current_rm.active_visitor_chat
            )
            if not rm_is_online:
                from RMPortal.services import assign_or_fallback
                # Tell the old (now offline) RM's inbox to drop the card
                if current_rm:
                    async_to_sync(get_channel_layer().group_send)(
                        f"visitor_inbox_rm_{current_rm.id}",
                        {"type": "visitor_removed", "conversation_id": active_convo.id},
                    )
                # Close the old convo so history stays with old RM (privacy)
                active_convo.status = "reassigned"
                active_convo.save(update_fields=["status"])
                # Night-hours hard gate — never assign a new RM, force night_chat missed
                if is_night_hours():
                    new_convo = VisitorConversation.objects.create(
                        visitor=visitor,
                        rm=None,
                        status="missed",
                        missed_reason="night_chat",
                        closed_at=timezone.now(),
                    )
                    from RMPortal.services import (
                        send_visitor_fallback_message,
                        build_fallback_payload,
                    )
                    if not new_convo.fallback_sent:
                        send_visitor_fallback_message(new_convo)
                        new_convo.fallback_sent = True
                        new_convo.save(update_fields=["fallback_sent"])
                    resp_data = {
                        "session_key": visitor.session_key,
                        "cookie_id": cookie_id,
                        "conversation_id": new_convo.id,
                        "rm_assigned": False,
                        "any_rm_online": False,
                        "fallback": build_fallback_payload(),
                    }
                    resp = JsonResponse(resp_data)
                    resp.set_cookie("vcid", cookie_id, max_age=365 * 24 * 3600, samesite="Lax")
                    return resp
                new_rm, new_convo = assign_or_fallback(visitor)
                # Notify the newly-assigned RM (if any) that a visitor landed
                if new_rm and new_convo:
                    async_to_sync(get_channel_layer().group_send)(
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
                            "is_returning": True,
                        },
                    )
                resp_data = {
                    "session_key": visitor.session_key,
                    "cookie_id": cookie_id,
                    "conversation_id": new_convo.id if new_convo else None,
                    "rm_assigned": new_rm is not None,
                    "any_rm_online": new_rm is not None,
                }
                if not new_rm:
                    from RMPortal.services import build_fallback_payload
                    resp_data["fallback"] = build_fallback_payload()
                resp = JsonResponse(resp_data)
                resp.set_cookie("vcid", cookie_id, max_age=365*24*3600, samesite="Lax")
                return resp

            resp = JsonResponse({
                "session_key": visitor.session_key,
                "cookie_id": cookie_id,
                "conversation_id": active_convo.id,
                "rm_assigned": True,
                "any_rm_online": True,
            })
            resp.set_cookie("vcid", cookie_id, max_age=365*24*3600, samesite="Lax")
            return resp

    referrer = body.get("referrer", "")[:500]
    utm_source = body.get("utm_source", "")[:100]
    utm_medium = body.get("utm_medium", "")[:100]
    utm_campaign = body.get("utm_campaign", "")[:100]
    current_url = body.get("url", "")[:500]
    page_title = body.get("title", "")[:200]

    ip = _get_client_ip(request)
    ua_string = request.META.get("HTTP_USER_AGENT", "")

    ua_info = parse_user_agent(ua_string)

    # Check if returning visitor (same cookie_id)
    existing = None
    if cookie_id:
        existing = (
            VisitorSession.objects
            .filter(cookie_id=cookie_id)
            .select_related("assigned_rm")
            .order_by("-first_seen_at")
            .first()
        )

    # Spec §5 — night hours hard gate: 12:00 AM to 9:30 AM IST, never assign an RM
    night = is_night_hours()

    if existing:
        # Returning visitor — use same RM if online, else assign new online RM
        old_rm = existing.assigned_rm
        if night:
            rm = None
        elif old_rm and old_rm.is_active and old_rm.active_visitor_chat:
            rm = old_rm
        else:
            rm = assign_rm_for_visitor()

        session_key = str(uuid.uuid4()).replace("-", "")
        visitor = VisitorSession.objects.create(
            session_key=session_key,
            cookie_id=cookie_id,
            ip_address=ip or "0.0.0.0",
            user_agent=ua_string,
            browser=ua_info["browser"],
            os=ua_info["os"],
            device_type=ua_info["device_type"],
            referrer=referrer,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            assigned_rm=rm,
            is_returning=True,
            name=existing.name,
            email=existing.email,
            phone=existing.phone,
        )

    else:
        # New visitor — geo lookup + assign RM (unless night hours)
        geo = get_visitor_geo(ip)
        session_key = str(uuid.uuid4()).replace("-", "")
        new_cookie_id = cookie_id or str(uuid.uuid4()).replace("-", "")
        rm = None if night else assign_rm_for_visitor()

        visitor = VisitorSession.objects.create(
            session_key=session_key,
            cookie_id=new_cookie_id,
            ip_address=ip or "0.0.0.0",
            country=geo.get("country"),
            city=geo.get("city"),
            region=geo.get("region"),
            isp=geo.get("isp"),
            user_agent=ua_string,
            browser=ua_info["browser"],
            os=ua_info["os"],
            device_type=ua_info["device_type"],
            referrer=referrer,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            assigned_rm=rm,
            is_returning=False,
        )
        cookie_id = new_cookie_id

    # Create a conversation for this session — always.
    # RM assigned → "waiting"; no RM + night → "missed"/night_chat; no RM → "missed"/no_rm.
    fallback_payload = None
    if rm:
        convo = VisitorConversation.objects.create(visitor=visitor, rm=rm, status="waiting")
    else:
        convo = VisitorConversation.objects.create(
            visitor=visitor,
            rm=None,
            status="missed",
            missed_reason="night_chat" if night else "no_rm",
            closed_at=timezone.now(),
        )
        from RMPortal.services import send_visitor_fallback_message, build_fallback_payload
        send_visitor_fallback_message(convo)
        convo.fallback_sent = True
        convo.save(update_fields=["fallback_sent"])
        # Include payload in the HTTP response too — the WebSocket may not be
        # connected yet at this point, so the broadcast can be missed.
        fallback_payload = build_fallback_payload()

    # Always track page view
    VisitorPageView.objects.create(visitor=visitor, url=current_url, page_title=page_title)
    visitor.page_count = 1
    visitor.save(update_fields=["page_count"])

    if rm:
        # Notify RM inbox via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"visitor_inbox_rm_{rm.id}",
            {
                "type": "visitor_new_session",
                "session_key": session_key,
                "conversation_id": convo.id,
                "visitor_name": visitor.name or visitor.email or visitor.ip_address,
                "ip": ip,
                "country": visitor.country,
                "city": visitor.city,
                "device_type": visitor.device_type,
                "current_page": current_url,
                "is_returning": visitor.is_returning,
            }
        )

    any_rm_online = RM.objects.filter(is_active=True, active_visitor_chat=True).exists()

    response_data = {
        "session_key": session_key,
        "cookie_id": cookie_id,
        "conversation_id": convo.id,
        "rm_assigned": rm is not None,
        "any_rm_online": any_rm_online,
    }
    if fallback_payload:
        response_data["fallback"] = fallback_payload

    response = JsonResponse(response_data)
    response.set_cookie("vcid", cookie_id, max_age=365 * 24 * 3600, httponly=True, samesite="Lax")
    return response


@csrf_exempt
def visitor_identify(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
    except Exception:
        body = {}

    session_key = (body.get("session_key") or "").strip()
    if not session_key:
        return JsonResponse({"error": "session_key required"}, status=400)

    update = {}
    if body.get("name"):
        update["name"] = str(body["name"])[:100]
    if body.get("email"):
        update["email"] = str(body["email"])[:254]
    if body.get("phone"):
        update["phone"] = str(body["phone"])[:20]

    if update:
        VisitorSession.objects.filter(session_key=session_key).update(**update)

        # Also update open conversation's visitor reference for inbox display
        try:
            visitor = VisitorSession.objects.select_related("assigned_rm").get(session_key=session_key)
            convo = VisitorConversation.objects.filter(
                visitor=visitor, status__in=["waiting", "active"]
            ).last()
            if convo and visitor.assigned_rm_id:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"visitor_inbox_rm_{visitor.assigned_rm_id}",
                    {
                        "type": "visitor_inbox_update",
                        "conversation_id": convo.id,
                        "visitor_name": update.get("name") or visitor.name or visitor.email or visitor.ip_address,
                        "preview": convo.last_message_preview,
                        "unread": convo.unread_count_rm,
                        "direction": convo.last_message_direction,
                        "time": convo.last_message_at.isoformat() if convo.last_message_at else "",
                        "notify": False,
                    }
                )
        except VisitorSession.DoesNotExist:
            pass

    return JsonResponse({"status": "ok"})


@csrf_exempt
def visitor_send_message(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
    except Exception:
        body = {}

    session_key = (body.get("session_key") or "").strip()
    text = (body.get("body") or "").strip()
    if not session_key or not text:
        return JsonResponse({"error": "session_key and body required"}, status=400)

    try:
        visitor = VisitorSession.objects.select_related("assigned_rm").get(session_key=session_key)
    except VisitorSession.DoesNotExist:
        return JsonResponse({"error": "invalid session"}, status=404)

    from RMPortal.services import assign_or_fallback, pick_rm_for_visitor, reassign_convo_to_new_rm

    convo = VisitorConversation.objects.filter(
        visitor=visitor, status__in=["waiting", "active"]
    ).first()

    # If convo's RM is now offline, do a proper reassignment:
    # old convo -> 'reassigned' (old RM still sees it), new convo for new RM.
    if convo and convo.rm_id:
        if not (convo.rm and convo.rm.is_active and convo.rm.active_visitor_chat):
            new_rm = pick_rm_for_visitor(visitor)
            if new_rm and new_rm.id != convo.rm_id:
                convo = reassign_convo_to_new_rm(convo, new_rm)

    # No open convo — re-assign or trigger fallback
    if not convo:
        _rm, convo = assign_or_fallback(visitor)

    if not convo:
        return JsonResponse({"error": "no active conversation"}, status=404)

    msg = VisitorMessage.objects.create(conversation=convo, direction="visitor", body=text)

    now = timezone.now()
    update_fields = ["last_message_at", "last_message_preview", "last_message_direction", "unread_count_rm"]
    convo.last_message_at = now
    convo.last_message_preview = text[:100]
    convo.last_message_direction = "visitor"
    convo.unread_count_rm += 1
    if not convo.visitor_first_message_at:
        convo.visitor_first_message_at = now
        update_fields.append("visitor_first_message_at")
    # NOTE: visitor messages NEVER flip status to "active".
    # Only an RM reply can activate the conversation.
    convo.save(update_fields=update_fields)

    msg_data = {
        "id": msg.id,
        "conversation_id": convo.id,
        "body": text,
        "direction": "visitor",
        "message_type": "text",
        "time": msg.created_at.strftime("%H:%M"),
        "date": msg.created_at.strftime("%Y-%m-%d"),
    }

    if visitor.assigned_rm_id:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"visitor_chat_{convo.id}",
            {"type": "visitor_chat_message", "message": msg_data}
        )
        async_to_sync(channel_layer.group_send)(
            f"visitor_inbox_rm_{visitor.assigned_rm_id}",
            {
                "type": "visitor_inbox_update",
                "conversation_id": convo.id,
                "visitor_name": visitor.name or visitor.email or visitor.ip_address,
                "preview": text[:80],
                "unread": convo.unread_count_rm,
                "direction": "visitor",
                "time": now.isoformat(),
                "notify": True,
            }
        )

    # If no RM was assigned, trigger the WhatsApp fallback (greeting + quick-sends)
    if not visitor.assigned_rm_id or not convo.rm_id:
        from RMPortal.services import send_visitor_fallback_message
        send_visitor_fallback_message(convo)

    return JsonResponse({"status": "ok", "message": msg_data})


@csrf_exempt
def visitor_send_file(request):
    """Visitor uploads image/file → saved → forwarded to RM."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    session_key = (request.POST.get("session_key") or "").strip()
    upload = request.FILES.get("file")
    if not session_key or not upload:
        return JsonResponse({"error": "session_key and file required"}, status=400)

    try:
        visitor = VisitorSession.objects.select_related("assigned_rm").get(session_key=session_key)
    except VisitorSession.DoesNotExist:
        return JsonResponse({"error": "invalid session"}, status=404)

    convo = VisitorConversation.objects.filter(visitor=visitor, status__in=["waiting", "active"]).first()
    if not convo:
        return JsonResponse({"error": "no active conversation"}, status=404)

    mime = upload.content_type or ""
    msg_type = "image" if mime.startswith("image/") else "file"

    msg = VisitorMessage.objects.create(
        conversation=convo, direction="visitor", message_type=msg_type, file=upload
    )
    now = timezone.now()
    convo.last_message_at = now
    convo.last_message_preview = f"[{'Image' if msg_type == 'image' else 'File'}]"
    convo.last_message_direction = "visitor"
    convo.unread_count_rm += 1
    convo.save(update_fields=["last_message_at", "last_message_preview", "last_message_direction", "unread_count_rm"])

    msg_data = {
        "id": msg.id,
        "direction": "visitor",
        "message_type": msg_type,
        "file_url": request.build_absolute_uri(msg.file.url),
        "file_name": upload.name,
        "time": timezone.localtime(msg.created_at).strftime("%I:%M %p"),
    }

    if visitor.assigned_rm_id:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"visitor_chat_{convo.id}",
            {"type": "visitor_chat_message", "message": msg_data}
        )
        async_to_sync(channel_layer.group_send)(
            f"visitor_inbox_rm_{visitor.assigned_rm_id}",
            {
                "type": "visitor_inbox_update",
                "conversation_id": convo.id,
                "visitor_name": visitor.name or visitor.email or visitor.ip_address,
                "preview": msg_data["file_url"][:80],
                "unread": convo.unread_count_rm,
                "direction": "visitor",
                "time": now.isoformat(),
                "notify": True,
            }
        )

    return JsonResponse({"status": "ok", "message": msg_data})


@rm_login_required
def visitor_send_rm_file(request, convo_id):
    """RM uploads image/file → saved → forwarded to visitor."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    rm = request.rm
    convo = get_object_or_404(VisitorConversation, id=convo_id, rm_id=rm.id)

    # Block sending if RM's visitor chat is off
    if not rm.active_visitor_chat:
        return JsonResponse({"error": "You are offline. Go online to send files."}, status=403)

    # Block sending on reassigned/closed/missed conversations
    if convo.status in ("reassigned", "closed", "missed"):
        return JsonResponse({"error": "This conversation is no longer active."}, status=403)

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"error": "file required"}, status=400)

    mime = upload.content_type or ""
    msg_type = "image" if mime.startswith("image/") else "file"

    msg = VisitorMessage.objects.create(
        conversation=convo, direction="rm", message_type=msg_type, file=upload
    )
    now = timezone.now()
    convo.last_message_at = now
    convo.last_message_preview = f"[{'Image' if msg_type == 'image' else 'File'}]"
    convo.last_message_direction = "rm"
    convo.unread_count_visitor += 1
    convo.unread_count_rm = 0
    convo.save(update_fields=["last_message_at", "last_message_preview", "last_message_direction", "unread_count_visitor", "unread_count_rm"])

    msg_data = {
        "id": msg.id,
        "direction": "rm",
        "message_type": msg_type,
        "file_url": request.build_absolute_uri(msg.file.url),
        "file_name": upload.name,
        "time": timezone.localtime(msg.created_at).strftime("%I:%M %p"),
    }

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"visitor_chat_{convo.id}",
        {"type": "visitor_chat_message", "message": msg_data}
    )
    async_to_sync(channel_layer.group_send)(
        f"visitor_{convo.visitor.session_key}",
        {"type": "visitor_rm_message", "message": msg_data}
    )

    return JsonResponse({"status": "ok", "message": msg_data})


#rm portal views



@rm_login_required
def visitor_messages_partial(request, convo_id):
    """HTMX partial — load messages for a visitor conversation."""
    rm = request.rm
    convo = get_object_or_404(VisitorConversation, id=convo_id, rm_id=rm.id)

    VisitorConversation.objects.filter(id=convo_id, rm_id=rm.id).update(unread_count_rm=0)
    VisitorMessage.objects.filter(conversation=convo, direction="visitor", is_read=False).update(is_read=True)

    # Notify visitor that RM has read the messages
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"visitor_{convo.visitor.session_key}",
        {
            "type": "visitor_rm_joined",
            "rm_name": convo.rm.rm_name if convo.rm else "RM",
        }
    )

    # Previous closed conversations from the same visitor — only THIS RM's chats (privacy)
    past_conversations = []
    if convo.visitor.cookie_id:
        past_conversations = (
            VisitorConversation.objects
            .filter(
                visitor__cookie_id=convo.visitor.cookie_id,
                rm_id=rm.id,
                status__in=["closed", "missed", "reassigned"]
            )
            .exclude(id=convo.id)
            .prefetch_related("messages")
            .order_by("-created_at")[:5]
        )

    return render(request, "partials/visitor_messages.html", {
        "convo": convo,
        "messages": convo.messages.all(),
        "past_conversations": past_conversations,
    })


@rm_login_required
def visitor_send(request, convo_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    rm = request.rm
    convo = get_object_or_404(VisitorConversation, id=convo_id, rm_id=rm.id)

    # Block sending if RM's visitor chat is off
    if not rm.active_visitor_chat:
        return JsonResponse({"error": "You are offline. Go online to send messages."}, status=403)

    # Block sending on reassigned/closed/missed conversations
    if convo.status in ("reassigned", "closed", "missed"):
        return JsonResponse({"error": "This conversation is no longer active."}, status=403)

    text = request.POST.get("body", "").strip()
    if not text:
        return JsonResponse({"error": "Empty message"}, status=400)

    msg = VisitorMessage.objects.create(conversation=convo, direction="rm", body=text)

    now = timezone.now()
    update_fields = ["last_message_at", "last_message_preview", "last_message_direction",
                     "unread_count_visitor", "unread_count_rm"]
    convo.last_message_at = now
    convo.last_message_preview = text[:100]
    convo.last_message_direction = "rm"
    convo.unread_count_visitor += 1
    convo.unread_count_rm = 0

    if not convo.rm_first_response_at:
        convo.rm_first_response_at = now
        update_fields.append("rm_first_response_at")
        if convo.visitor_first_message_at:
            convo.response_time_seconds = int((now - convo.visitor_first_message_at).total_seconds())
            update_fields.append("response_time_seconds")

    if convo.status == "waiting":
        convo.status = "active"
        update_fields.append("status")

    convo.save(update_fields=update_fields)

    msg_data = {
        "id": msg.id,
        "conversation_id": convo.id,
        "body": text,
        "direction": "rm",
        "message_type": "text",
        "time": msg.created_at.strftime("%H:%M"),
        "date": msg.created_at.strftime("%Y-%m-%d"),
    }

    channel_layer = get_channel_layer()
    # Push to RM chat WebSocket group
    async_to_sync(channel_layer.group_send)(
        f"visitor_chat_{convo.id}",
        {"type": "visitor_chat_message", "message": msg_data}
    )
    # Push to visitor WebSocket
    async_to_sync(channel_layer.group_send)(
        f"visitor_{convo.visitor.session_key}",
        {"type": "visitor_rm_message", "message": msg_data}
    )

    return JsonResponse({"status": "ok", "message": msg_data})


@rm_login_required
def visitor_close_conversation(request, convo_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    rm = request.rm
    convo = get_object_or_404(VisitorConversation, id=convo_id, rm_id=rm.id)

    convo.status = "closed"
    convo.closed_at = timezone.now()
    convo.save(update_fields=["status", "closed_at"])

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"visitor_{convo.visitor.session_key}",
        {"type": "visitor_conversation_closed"}
    )

    return JsonResponse({"status": "closed"})


@rm_login_required
def visitor_force_offline(request, rm_code):
    """
    Spec §10 — called by a front-end idle timer (e.g. 3 min no activity).
    Forces the RM offline, reassigns waiting visitors, closes session.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    rm = request.rm
    if getattr(rm, "rm_code", None) != rm_code:
        return redirect("webchat", rm_code=rm.rm_code)

    if rm.active_visitor_chat:
        rm.active_visitor_chat = False
        rm.save(update_fields=["active_visitor_chat"])
        from RMPortal.services import reassign_rm_conversations
        reassign_rm_conversations(rm)

    # Close the active login row
    from django.db.models import F
    from dashboard.models import RMLoginHistory
    now = timezone.now()
    RMLoginHistory.objects.filter(rm=rm, status=True).update(
        logout_time=now, status=False, duration=now - F("login_time")
    )

    request.session.flush()
    return JsonResponse({"status": "offline"})


@rm_login_required
def whatsapp_status_toggle(request, rm_code):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    from django.utils import timezone as tz
    rm = request.rm
    if getattr(rm, "rm_code", None) != rm_code:
        return redirect("webchat", rm_code=rm.rm_code)
    going_online = not rm.active_whatsapp
    rm.active_whatsapp = going_online
    fields = ["active_whatsapp"]
    if going_online:
        # Record the moment this RM came online so FCFS ordering works:
        # earliest online_since = smallest last_assigned_at = first in queue.
        rm.last_assigned_at = tz.now()
        fields.append("last_assigned_at")
    rm.save(update_fields=fields)

    return JsonResponse({"active_whatsapp": rm.active_whatsapp})


@rm_login_required
def visitor_chat_status_toggle(request, rm_code):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    rm = request.rm
    if getattr(rm, "rm_code", None) != rm_code:
        return redirect("webchat", rm_code=rm.rm_code)

    # Spec §5 — RM cannot go online during night hours (12 AM - 9:30 AM IST)
    going_online = not rm.active_visitor_chat
    if going_online and is_night_hours():
        return JsonResponse(
            {
                "error": "Cannot go online between 12:00 AM and 9:30 AM. "
                         "Visitor chat is available from 9:30 AM onwards.",
                "active_visitor_chat": False,
            },
            status=403,
        )

    going_online_visitor = not rm.active_visitor_chat
    rm.active_visitor_chat = going_online_visitor
    vc_fields = ["active_visitor_chat"]
    if going_online_visitor:
        from django.utils import timezone as tz
        rm.last_visitor_assigned_at = tz.now()
        vc_fields.append("last_visitor_assigned_at")
    rm.save(update_fields=vc_fields)

    # When RM goes offline, reassign all their open conversations to next online RM
    if not rm.active_visitor_chat:
        from RMPortal.services import reassign_rm_conversations
        reassign_rm_conversations(rm)

    return JsonResponse({"active_visitor_chat": rm.active_visitor_chat})
