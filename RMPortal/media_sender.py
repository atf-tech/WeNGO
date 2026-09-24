"""Background delivery of an RM's media batch to WhatsApp — one file at a time, in the order picked."""

import threading
import time

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import close_old_connections
from django.utils import timezone
from datetime import timedelta

from .models import Conversation, Message, MessageMedia
from .services import (
    send_whatsapp_media_message,
    send_whatsapp_template,
    upload_media_to_whatsapp,
)
from .utils import convert_webm_to_ogg

import logging
logger = logging.getLogger(__name__)

# How many files an RM may attach in one go.
MAX_MEDIA_PER_SEND = 20

# Meta's upload ceilings per media type (bytes) — bigger files are rejected by the Cloud API.
MEDIA_SIZE_LIMITS = {
    "image": 5 * 1024 * 1024,
    "video": 16 * 1024 * 1024,
    "audio": 16 * 1024 * 1024,
    "document": 100 * 1024 * 1024,
}

# Small gap between sends so the donor receives the files in the order the RM picked them.
SEND_GAP_SECONDS = 0.3


def queue_media_batch(conversation_id, media_ids):
    """Deliver already-saved media rows in a daemon thread so the RM's chat stays instant."""
    thread = threading.Thread(
        target=deliver_media_batch,
        args=(conversation_id, list(media_ids)),
        name=f"wa-media-{conversation_id}",
        daemon=True,
    )
    thread.start()


def deliver_media_batch(conversation_id, media_ids):
    """Upload each file to WhatsApp and send it; a failure marks only that message failed."""
    close_old_connections()
    try:
        conversation = (
            Conversation.objects
            .select_related("donor")
            .filter(id=conversation_id)
            .first()
        )
        if not conversation:
            return

        if is_outside_24h_window(conversation):
            # Reopen the 24-hr window once for the whole batch, not once per file.
            try:
                wa_pid, wa_token = _get_wa_creds_for_convo(conversation)
                send_whatsapp_template(
                    to=conversation.donor.phone_number,
                    template_name="rm_followup_message",
                    phone_number_id=wa_pid,
                    access_token=wa_token,
                )
                time.sleep(1)
            except Exception:
                logger.exception("WhatsApp template send failed")

        for media_id in media_ids:
            media = MessageMedia.objects.select_related("message").filter(id=media_id).first()
            if not media:
                continue
            try:
                deliver_one(conversation, media)
            except Exception:
                logger.exception("WhatsApp media send failed")
                mark_failed(conversation, media.message)
            time.sleep(SEND_GAP_SECONDS)
    finally:
        close_old_connections()


def _get_wa_creds_for_convo(conversation):
    """Return (phone_number_id, access_token) for the conversation's RM branch."""
    rm = conversation.rm
    branch = getattr(rm, "rm_branch", "") or ""
    wa = getattr(conversation, "_wa_creds", None)
    if wa is None:
        from django.conf import settings
        wa = settings.WA_NUMBERS.get(branch, {})
    return (
        wa.get("phone_number_id", getattr(settings, "WA_PHONE_NUMBER_ID", "")),
        wa.get("access_token", getattr(settings, "WA_ACCESS_TOKEN", "")),
    )


def is_outside_24h_window(conversation):
    """True when the donor's last inbound message is missing or older than 24 hours."""
    last_incoming = (
        conversation.messages
        .filter(direction="in")
        .order_by("-created_at")
        .first()
    )
    return (
        last_incoming is None or
        timezone.now() - last_incoming.created_at > timedelta(hours=24)
    )


def deliver_one(conversation, media):
    """Upload a single media file to WhatsApp and send it to the donor."""
    message = media.message
    file_path = media.file.path
    mime_type = media.mime_type

    if message.message_type == "audio" and mime_type == "audio/webm":
        webm_path, ogg_path = convert_webm_to_ogg(media.file)
        file_path = ogg_path
        mime_type = "audio/ogg"

    wa_pid, wa_token = _get_wa_creds_for_convo(conversation)
    media.wa_media_id = upload_media_to_whatsapp(file_path, mime_type, phone_number_id=wa_pid, access_token=wa_token)
    media.save(update_fields=["wa_media_id"])

    res = send_whatsapp_media_message(
        conversation.donor.phone_number,
        media.wa_media_id,
        message.message_type,
        phone_number_id=wa_pid,
        access_token=wa_token,
    )
    message.external_id = res["messages"][0]["id"]
    message.save(update_fields=["external_id"])


def mark_failed(conversation, message):
    """Flag a message the donor never received so the RM can retry it."""
    message.status = "failed"
    message.save(update_fields=["status"])

    last_msg = Message.objects.filter(conversation=conversation).order_by("-id").first()
    if last_msg and last_msg.id == message.id:
        conversation.last_message_status = "failed"
        conversation.save(update_fields=["last_message_status"])

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{conversation.id}",
        {
            "type": "message_status",
            "message_id": message.id,
            "status": "failed",
        }
    )
    async_to_sync(channel_layer.group_send)(
        f"inbox_rm_{conversation.rm_id}",
        {
            "type": "inbox_update",
            "conversation_id": conversation.id,
            "phone": conversation.donor.phone_number,
            "preview": conversation.last_message_preview,
            "unread": conversation.unread_count,
            "direction": "out",
            "status": "failed",
            "message_type": conversation.last_message_type,
            "time": conversation.last_message_at.strftime("%I:%M %p") if conversation.last_message_at else "",
        }
    )


def validate_media_batch(uploads, message_types):
    """Return an error message for a rejected batch, or None when every file can be sent."""
    if not uploads:
        return "No file selected."
    if len(uploads) > MAX_MEDIA_PER_SEND:
        return f"You can send at most {MAX_MEDIA_PER_SEND} files at a time."
    if len(message_types) != len(uploads):
        return "Media type missing for one of the files."

    for uploaded, message_type in zip(uploads, message_types):
        if message_type not in MEDIA_SIZE_LIMITS:
            return f"Unsupported media type: {message_type}."
        if uploaded.size > MEDIA_SIZE_LIMITS[message_type]:
            limit_mb = MEDIA_SIZE_LIMITS[message_type] // (1024 * 1024)
            return f"{uploaded.name} is too large — WhatsApp allows {message_type} files up to {limit_mb} MB."
    return None
