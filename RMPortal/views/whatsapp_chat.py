from datetime import timedelta

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Max
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.decorators.http import require_POST

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from dashboard.models import *
from dashboard.models import RM
from RMPortal.models import (
    Conversation, Message, MessageMedia,
    VisitorConversation,
)
from RMPortal.utils import convert_webm_to_ogg
from RMPortal.services import (
    send_whatsapp_message,
    send_whatsapp_template,
    upload_media_to_whatsapp,
    send_whatsapp_media_message,
    mark_whatsapp_message_as_read,
)

from .auth import rm_login_required


def _get_wa_creds(rm):
    """Return (phone_number_id, access_token) for the RM's branch."""
    branch = rm.rm_branch or ""
    wa = settings.WA_NUMBERS.get(branch, {})
    return (
        wa.get("phone_number_id", settings.WA_PHONE_NUMBER_ID),
        wa.get("access_token", settings.WA_ACCESS_TOKEN),
    )


@rm_login_required
def whatsapp(request, rm_code):
    rm = request.rm
    if getattr(rm, "rm_code", None) != rm_code:
        return redirect("webchat", rm_code=rm.rm_code)

    # Opportunistic sweep: flip waiting convos older than 30min to missed.
    from RMPortal.services import expire_stale_waiting_conversations
    expire_stale_waiting_conversations()

    # ✅ mark all inactive when opening inbox
    Conversation.objects.filter(rm=rm).update(is_active=False)

    conversations = (
        Conversation.objects
        .select_related("donor")
        .filter(rm=rm, status="open")
        .order_by("-last_message_at")
    )

    # Show waiting, active, missed, reassigned — everything except "closed"
    # (explicit list so missed/quickly_left/etc are clearly included)
    visitor_conversations = (
        VisitorConversation.objects
        .filter(rm=rm, status__in=["waiting", "active", "missed", "reassigned"])
        .select_related("visitor")
        .annotate(sort_time=Coalesce("last_message_at", "created_at"))
        .order_by("-sort_time")
    )

    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    # Spec §12 — RM dashboard today-counters
    rm_today = VisitorConversation.objects.filter(
        rm=rm,
        created_at__gte=today_start,
        created_at__lt=tomorrow_start,
    )

    count_active = rm_today.filter(status="active").count()
    count_reassigned = rm_today.filter(status="reassigned").count()

    # quickly_left — visitor left within 5s (reason ≠ night_chat)
    count_quickly_left = rm_today.filter(
        status="missed",
        visitor__total_time_seconds__lte=5,
    ).exclude(missed_reason="night_chat").count()

    # missed — status missed AND total_time > 5 AND reason ≠ night_chat
    count_missed = rm_today.filter(
        status="missed",
        visitor__total_time_seconds__gt=5,
    ).exclude(missed_reason="night_chat").count()

    # Night chat — any missed convo with reason night_chat (not tied to RM)
    count_night_chat = rm_today.filter(
        status="missed",
        missed_reason="night_chat",
    ).count()

    # RM was online but didn't reply
    missed_no_reply = rm_today.filter(
        status="missed",
        rm_first_response_at__isnull=True,
    ).count()

    # Visitors that came while THIS RM was offline: calculate using RMLoginHistory
    missed_while_offline = 0
    try:
        # Current active login record for this RM (should exist after rm_login)
        current_login = RMLoginHistory.objects.filter(rm=rm, status=True).order_by('-login_time').first()
        if current_login:
            # Find the previous login/logout record (the one immediately before current)
            prev = RMLoginHistory.objects.filter(rm=rm, login_time__lt=current_login.login_time).order_by('-login_time').first()
            if prev and prev.logout_time:
                missed_while_offline = VisitorConversation.objects.filter(
                    created_at__gt=prev.logout_time,
                    created_at__lte=current_login.login_time
                ).count()
    except Exception:
        missed_while_offline = 0

    # Provide both `count_*` and template-friendly names used elsewhere
    return render(request, "whatsapp.html", {
        "rm": rm,
        "count_active": count_active,
        "count_reassigned": count_reassigned,
        "count_quickly_left": count_quickly_left,
        "count_missed": count_missed,
        "count_night_chat": count_night_chat,
        # Template expects these variable names in some places — keep both
        "active_count": count_active,
        "reassigned_count": count_reassigned,
        "quickly_left_count": count_quickly_left,
        "missed_count": count_missed,
        "night_chat_count": count_night_chat,
        "missed_no_reply": missed_no_reply,
        "missed_while_offline": missed_while_offline,
        "conversations": conversations,
        "visitor_conversations": visitor_conversations,
    })



@rm_login_required
def conversation(request, convo_id):
    rm = request.rm
    if not rm:
        return redirect("rm_login")

    Conversation.objects.filter(rm=rm).update(is_active=False)


    conversation = get_object_or_404(
        Conversation,
        id=convo_id,
        rm=rm
    )

    conversation.is_active = True
    conversation.unread_count = 0
    last_msg = conversation.messages.order_by("-id").first()
    old_last_seen = conversation.last_seen_message_id

    conversation.last_seen_at = timezone.now()
    conversation.last_seen_message_id = last_msg.id if last_msg else None
    conversation.unread_count = 0
    conversation.is_active = True

    conversation.save(update_fields=[
        "last_seen_at",
        "last_seen_message_id",
        "unread_count",
        "is_active"
    ])

    
    wa_pid, wa_token = _get_wa_creds(rm)
    unread_incoming_messages = conversation.messages.filter(
        direction="in",
        id__gt=old_last_seen if old_last_seen else 0,  # ✅ uses OLD value
    external_id__isnull=False
    )

    for msg in unread_incoming_messages:
        mark_whatsapp_message_as_read(msg.external_id, phone_number_id=wa_pid, access_token=wa_token)



    # ✅ notify inbox to remove badge instantly
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"inbox_rm_{rm.id}",
        {
            "type": "inbox_update",
            "conversation_id": conversation.id,
            "preview": conversation.last_message_preview,
            "unread": 0,
            "direction": conversation.last_message_direction,
            "status": conversation.last_message_status,
            "message_type": conversation.last_message_type,
            "time": conversation.last_message_at.strftime("%I:%M %p") if conversation.last_message_at else "",
        }
    )

    return render(request, "conversation.html", {
        "conversation": conversation,
        "messages": conversation.messages.all()
    })



@rm_login_required
def mark_inactive(request, convo_id):
    rm = request.rm
    if not rm:
        return HttpResponse(status=403)

    Conversation.objects.filter(
        id=convo_id,
        rm_id=rm.id
    ).update(is_active=False)

    return HttpResponse(status=204)


@require_POST
@rm_login_required
def mark_active(request, convo_id):
    rm = request.rm

    if not rm:
        return HttpResponse(status=403)

    # 🔥 get last message id
    last_msg_id = Message.objects.filter(
        conversation_id=convo_id
    ).aggregate(max_id=Max("id"))["max_id"]

    Conversation.objects.filter(
        id=convo_id,
        rm_id=rm.id
    ).update(
        is_active=True,
        unread_count=0,
        last_seen_message_id=last_msg_id,
        last_seen_at=timezone.now()
    )

    return HttpResponse(status=204)



@require_POST
@rm_login_required
def send_message(request, convo_id):
    text = (request.POST.get("text") or "").strip()
    rm = request.rm


    if not text:
        return HttpResponse(status=204)

    conversation = get_object_or_404(
        Conversation,
        id=convo_id,
        rm=rm
    )

    # 1️⃣ Save message
    message = Message.objects.create(
        conversation=conversation,
        direction="out",
        body=text,
        status="sent",
        message_type="text"
    )

    conversation.last_message_type = message.message_type
    conversation.last_message_status = message.status
    conversation.last_message_direction = message.direction
    conversation.last_message_preview = text.replace('\n', ' ').replace('\r', '').strip()
    conversation.last_message_at = message.created_at
    conversation.last_seen_message_id = message.id
    conversation.last_seen_at = timezone.now()
    conversation.unread_count = 0

    conversation.save(update_fields=[
    "last_message_type",
    "last_message_status",
    "last_message_direction",
    "last_message_preview",
    "last_message_at",
    "last_seen_message_id",
    "last_seen_at",
    "unread_count",
])



    local_time = timezone.localtime(message.created_at)
    channel_layer = get_channel_layer()

    # 2️⃣ 🔥 SEND CHAT MESSAGE (THIS WAS MISSING)
    async_to_sync(channel_layer.group_send)(
        f"chat_{conversation.id}",
        {
            "type": "chat_message",
            "message": {
                "id": message.id,
                "conversation_id": conversation.id,

                "body": message.body,
                "direction": "out",
                "message_type": "text",
                "status": message.status,
                "time": local_time.isoformat(),
                "date": local_time.strftime("%Y-%m-%d"),
            }
        }
    )

    async_to_sync(channel_layer.group_send)(
        f"inbox_rm_{rm.id}",
        {
            "type": "inbox_update",
            "conversation_id": conversation.id,
            "phone": conversation.donor.phone_number,
            "preview": text,
            "unread": conversation.unread_count,
            "direction": message.direction,
            "status": message.status,
            "message_type": message.message_type,
            "time": local_time.isoformat(),

        }
    )




    
    last_incoming = conversation.messages.filter(
        direction="in"
    ).order_by("-created_at").first()

    outside_window = (
        last_incoming is None or
        timezone.now() - last_incoming.created_at > timedelta(hours=24)
    )

    wa_pid, wa_token = _get_wa_creds(rm)

    try:
        if outside_window:
            try:
                send_whatsapp_template(
                    to=conversation.donor.phone_number,
                    template_name="rm_followup_message",
                    phone_number_id=wa_pid,
                    access_token=wa_token,
                )
                import time as time_module
                time_module.sleep(1)
            except Exception as tmpl_err:
                print("WhatsApp template send skipped:", tmpl_err)

        response = send_whatsapp_message(
            to=conversation.donor.phone_number,
            text=text,
            phone_number_id=wa_pid,
            access_token=wa_token,
        )

        message.external_id = response["messages"][0]["id"]
        message.save(update_fields=["external_id"])

    except Exception as e:
        print("WhatsApp send failed:", e)

    return HttpResponse(status=200)


@require_POST
@rm_login_required
def send_media_message(request, convo_id):
    rm = request.rm

    conversation = get_object_or_404(
    Conversation,
    id=convo_id,
    rm=rm
)


    uploaded = request.FILES.get("file")
    message_type = request.POST.get("message_type")

    if not uploaded or message_type not in ["image", "video", "audio", "document"]:
        return HttpResponse(status=400)

    # 1️⃣ Save message
    message = Message.objects.create(
        conversation=conversation,
        direction="out",
        message_type=message_type,
        status="sent"
    )

    # 🔥 Update conversation last message info
    conversation.last_message_type = message.message_type
    conversation.last_message_status = message.status
    conversation.last_message_direction = message.direction
    conversation.last_message_preview = ""   # no text for media
    conversation.last_message_at = message.created_at
    conversation.last_seen_message_id = message.id
    conversation.last_seen_at = timezone.now()
    conversation.unread_count = 0

    conversation.save(update_fields=[
    "last_message_type",
    "last_message_status",
    "last_message_direction",
    "last_message_preview",
    "last_message_at",
    "last_seen_message_id",
    "last_seen_at",
    "unread_count",
])




    media = MessageMedia.objects.create(
        message=message,
        file=uploaded,
        mime_type=uploaded.content_type,
        size=uploaded.size
    )

    channel_layer = get_channel_layer()

    local_time = timezone.localtime(message.created_at)

    async_to_sync(channel_layer.group_send)(
        f"chat_{conversation.id}",
        {
            "type": "chat_message",
            "message": {
                "id": message.id,
                "conversation_id": conversation.id,

                "direction": "out",
                "message_type": message_type,
                "file_url": media.file.url,
                "status": message.status,
                "time": local_time.isoformat(),
                "date": local_time.strftime("%Y-%m-%d"),
            }
        }
    )


    async_to_sync(channel_layer.group_send)(
        f"inbox_rm_{rm.id}",
        {
            "type": "inbox_update",
            "conversation_id": conversation.id,
            "phone": conversation.donor.phone_number,
            "preview": message.body or "",
            "unread": conversation.unread_count,
            "direction": "out",
            "status": message.status,
            "message_type": message_type,
            "time": local_time.isoformat(),

        }
    )


    wa_pid, wa_token = _get_wa_creds(rm)

    try:
        file_path = media.file.path
        mime_type = media.mime_type

        if message_type == "audio" and mime_type == "audio/webm":
            webm_path, ogg_path = convert_webm_to_ogg(media.file)
            file_path = ogg_path
            mime_type = "audio/ogg"
            print("Uploading:", file_path, mime_type)

        # 🔍 Check 24hr window before uploading
        last_incoming = conversation.messages.filter(
            direction="in"
        ).order_by("-created_at").first()

        outside_window = (
            last_incoming is None or
            timezone.now() - last_incoming.created_at > timedelta(hours=24)
        )

        if outside_window:
            try:
                send_whatsapp_template(
                    to=conversation.donor.phone_number,
                    template_name="rm_followup_message",
                    phone_number_id=wa_pid,
                    access_token=wa_token,
                )
                import time as time_module
                time_module.sleep(1)
            except Exception as tmpl_err:
                print("WhatsApp template send skipped:", tmpl_err)

        wa_media_id = upload_media_to_whatsapp(file_path, mime_type, phone_number_id=wa_pid, access_token=wa_token)
        media.wa_media_id = wa_media_id
        media.save(update_fields=["wa_media_id"])

        res = send_whatsapp_media_message(
            conversation.donor.phone_number,
            wa_media_id,
            message_type,
            phone_number_id=wa_pid,
            access_token=wa_token,
        )

        message.external_id = res["messages"][0]["id"]
        message.save(update_fields=["external_id"])

    except Exception as e:
        print("WhatsApp media send failed:", e)
    return HttpResponse(status=204)





@rm_login_required
def messages_partial(request, convo_id):
    rm = request.rm

    conversation = get_object_or_404(
        Conversation,
        id=convo_id,
        rm=rm
    )

 
    old_last_seen = conversation.last_seen_message_id

    last_msg = conversation.messages.order_by("-id").first()

    conversation.last_seen_at = timezone.now()
    conversation.last_seen_message_id = last_msg.id if last_msg else None
    conversation.unread_count = 0
    conversation.is_active = True

    conversation.save(update_fields=[
        "last_seen_at",
        "last_seen_message_id",
        "unread_count",
        "is_active"
    ])

    wa_pid, wa_token = _get_wa_creds(rm)
    unread_incoming = conversation.messages.filter(
        direction="in",
        id__gt=old_last_seen if old_last_seen else 0,
        external_id__isnull=False,
    )
    for msg in unread_incoming:
        try:
            mark_whatsapp_message_as_read(msg.external_id, phone_number_id=wa_pid, access_token=wa_token)
        except Exception as e:
            print("mark-as-read failed:", e)

    return render(request, "partials/messages.html", {
        "messages": conversation.messages.all(),
    })




@rm_login_required
def rmportal_index(request,rm_code="esfc"):
    return render(request, "RMPortal/index.html", {"rm": request.rm})


@rm_login_required
def rm_collection(request, rm_code=None):
    if rm_code and getattr(request.rm, "rm_code", None) != rm_code:
        return redirect("webchat", rm_code=request.rm.rm_code)
    return render(request, "RMPortal/rm_collection.html", {"rm": request.rm})





