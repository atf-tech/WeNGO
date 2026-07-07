import json
import hmac
import hashlib
import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .services import assign_rm, mark_whatsapp_message_as_read, _dedicated_branches
from .models import Donor, Conversation, Message, MessageMedia


def verify_signature(request):
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        return False

    app_secret = settings.WA_APP_SECRET
    if not app_secret:
        return False

    expected = "sha256=" + hmac.new(
        app_secret.encode(),
        request.body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


@csrf_exempt
def webhook(request):
    if request.method == "GET":
        if request.GET.get("hub.verify_token") == settings.VERIFY_TOKEN:
            return HttpResponse(request.GET.get("hub.challenge"))
        return HttpResponse(status=403)

    if request.method != "POST":
        return HttpResponse(status=200)

    if settings.WA_APP_SECRET and not verify_signature(request):
        return HttpResponse(status=403)

    try:
        payload = json.loads(request.body)
    except Exception as e:
        print("Webhook JSON error:", e)
        return JsonResponse({"status": "ignored"})

    channel_layer = get_channel_layer()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            for status_obj in value.get("statuses", []):
                wa_id = status_obj.get("id")
                wa_status = status_obj.get("status")
                if not wa_id or not wa_status:
                    continue

                try:
                    msg = Message.objects.get(external_id=wa_id)
                except Message.DoesNotExist:
                    continue

                if wa_status == "delivered":
                    msg.status = "delivered"
                elif wa_status == "read":
                    msg.status = "read"
                else:
                    continue

                msg.save(update_fields=["status"])
                conversation = msg.conversation

                last_msg = Message.objects.filter(conversation=conversation).order_by("-id").first()
                if last_msg and last_msg.id == msg.id:
                    conversation.last_message_status = msg.status
                    conversation.save(update_fields=["last_message_status"])

                async_to_sync(channel_layer.group_send)(
                    f"inbox_rm_{conversation.rm.id}",
                    {
                        "type": "inbox_update",
                        "conversation_id": conversation.id,
                        "phone": conversation.donor.phone_number,
                        "preview": conversation.last_message_preview,
                        "unread": conversation.unread_count,
                        "direction": "out",
                        "status": msg.status,
                        "message_type": conversation.last_message_type,
                        "time": conversation.last_message_at.strftime("%I:%M %p") if conversation.last_message_at else "",
                    }
                )

                async_to_sync(channel_layer.group_send)(
                    f"chat_{conversation.id}",
                    {
                        "type": "message_status",
                        "message_id": msg.id,
                        "status": msg.status,
                    }
                )

            messages = value.get("messages", [])
            if not messages:
                continue

            incoming_phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
            matching_branches = [
                b for b, creds in settings.WA_NUMBERS.items()
                if creds.get("phone_number_id") == incoming_phone_number_id
            ]
            wa_branch = matching_branches[0] if len(matching_branches) == 1 else None
            wa_creds = settings.WA_NUMBERS.get(wa_branch, {})
            wa_access_token = wa_creds.get("access_token", settings.WA_ACCESS_TOKEN)
            wa_phone_number_id = wa_creds.get("phone_number_id", settings.WA_PHONE_NUMBER_ID)

            for msg in messages:
                msg_id = msg.get("id")
                donor_number = msg.get("from")
                msg_type = msg.get("type")
                if not msg_id or not donor_number or not msg_type:
                    continue

                if Message.objects.filter(external_id=msg_id).exists():
                    continue

                donor, _ = Donor.objects.get_or_create(phone_number=donor_number)

                with transaction.atomic():
                    convo_qs = Conversation.objects.select_for_update().filter(
                        donor=donor,
                        status="open",
                    )
                    if wa_branch:
                        convo_qs = convo_qs.filter(rm__rm_branch=wa_branch)
                    else:
                        dedicated = _dedicated_branches()
                        if dedicated:
                            convo_qs = convo_qs.exclude(rm__rm_branch__in=dedicated)

                    conversation = convo_qs.first()

                    if not conversation:
                        previous = (
                            Conversation.objects
                            .filter(donor=donor, rm__isnull=False)
                            .order_by("-id")
                            .first()
                        )
                        dedicated = _dedicated_branches()
                        prev_branch = previous.rm.rm_branch if previous else None
                        reuse = previous and (
                            (wa_branch and prev_branch == wa_branch) or
                            (wa_branch is None and prev_branch not in dedicated)
                        )
                        if reuse:
                            rm = previous.rm
                        else:
                            rm = assign_rm(branch=wa_branch)
                            if not rm:
                                continue
                        conversation = Conversation.objects.create(
                            donor=donor,
                            rm=rm,
                            is_active=False,
                        )

                    if msg_type == "text":
                        body = msg.get("text", {}).get("body", "")
                        message = Message.objects.create(
                            conversation=conversation,
                            direction="in",
                            body=body,
                            message_type="text",
                            status="delivered",
                            external_id=msg_id,
                        )
                    else:
                        media_info = msg.get(msg_type, {})
                        wa_media_id = media_info.get("id")
                        if not wa_media_id:
                            continue

                        headers = {"Authorization": f"Bearer {wa_access_token}"}
                        meta_resp = requests.get(
                            f"https://graph.facebook.com/v21.0/{wa_media_id}",
                            headers=headers,
                            timeout=10,
                        )
                        if meta_resp.status_code != 200:
                            continue
                        meta = meta_resp.json()
                        media_resp = requests.get(
                            meta.get("url"),
                            headers=headers,
                            timeout=20,
                        )
                        if media_resp.status_code != 200:
                            continue

                        mime = meta.get("mime_type", "")
                        ext = mime.split("/")[-1] if "/" in mime else "bin"
                        filename = f"{wa_media_id}.{ext}"
                        path = default_storage.save(
                            f"whatsapp_media/{filename}",
                            ContentFile(media_resp.content),
                        )

                        message = Message.objects.create(
                            conversation=conversation,
                            direction="in",
                            message_type=msg_type,
                            status="delivered",
                            external_id=msg_id,
                        )
                        MessageMedia.objects.create(
                            message=message,
                            file=path,
                            mime_type=mime,
                            size=len(media_resp.content),
                            wa_media_id=wa_media_id,
                        )

                    conversation.last_message_type = message.message_type
                    conversation.last_message_status = message.status
                    conversation.last_message_direction = message.direction
                    conversation.last_message_at = message.created_at
                    conversation.last_message_preview = (
                        message.body.replace("\n", " ").replace("\r", "").strip()
                        if message.message_type == "text"
                        else "🎤 Voice message" if message.message_type == "audio"
                        else "🖼 Image" if message.message_type == "image"
                        else "🎥 Video" if message.message_type == "video"
                        else "📄 Document"
                    )

                    if conversation.last_seen_message_id:
                        unread = Message.objects.filter(
                            conversation=conversation,
                            direction="in",
                            id__gt=conversation.last_seen_message_id,
                        ).count()
                    else:
                        unread = Message.objects.filter(
                            conversation=conversation,
                            direction="in",
                        ).count()
                    conversation.unread_count = unread
                    conversation.save()

                    if conversation.is_active and message.external_id:
                        try:
                            mark_whatsapp_message_as_read(
                                message.external_id,
                                phone_number_id=wa_phone_number_id,
                                access_token=wa_access_token,
                            )
                        except Exception as e:
                            print("❌ read mark failed:", e)

                    local_time = timezone.localtime(message.created_at)
                    ws_payload = {
                        "id": message.id,
                        "conversation_id": conversation.id,
                        "direction": "in",
                        "message_type": message.message_type,
                        "status": message.status,
                        "time": local_time.isoformat(),
                        "date": local_time.strftime("%Y-%m-%d"),
                    }
                    if message.message_type == "text":
                        ws_payload["body"] = message.body
                    else:
                        media = MessageMedia.objects.filter(message=message).first()
                        if media:
                            ws_payload["file_url"] = media.file.url

                    async_to_sync(channel_layer.group_send)(
                        f"chat_{conversation.id}",
                        {"type": "chat_message", "message": ws_payload},
                    )
                    async_to_sync(channel_layer.group_send)(
                        f"inbox_rm_{conversation.rm.id}",
                        {
                            "type": "inbox_update",
                            "conversation_id": conversation.id,
                            "phone": donor.phone_number,
                            "preview": conversation.last_message_preview,
                            "unread": conversation.unread_count,
                            "direction": "in",
                            "status": message.status,
                            "message_type": message.message_type,
                            "time": local_time.isoformat(),
                            "notify": not conversation.is_active,
                        },
                    )

    return JsonResponse({"status": "ok"})
