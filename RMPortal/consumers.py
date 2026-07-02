import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import localtime
from RMPortal.models import Conversation, VisitorSession, VisitorConversation, VisitorMessage



class InboxConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.rm_id = self.scope["session"].get("rm_id")

        if not self.rm_id:
            await self.close()
            return

        self.group_name = f"inbox_rm_{self.rm_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()


    async def disconnect(self, close_code):
        if hasattr(self, "rm_id"):
            await self.channel_layer.group_discard(
                f"inbox_rm_{self.rm_id}",
                self.channel_name
            )

    async def inbox_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "inbox_update",
            "conversation_id": event["conversation_id"],
            "phone": event.get("phone"),           # ✅ ADD THIS
            "preview": event.get("preview"),
            "unread": event.get("unread", 0),
            "direction": event.get("direction"),
            "status": event.get("status"),
            "message_type": event.get("message_type"),
            "time": event.get("time"),
            "notify": event.get("notify", False),  # ✅ ADD THIS
        }))



class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.rm_id = self.scope["session"].get("rm_id")
        self.convo_id = self.scope["url_route"]["kwargs"]["convo_id"]

        if not self.rm_id:
            await self.close()
            return

        self.group_name = f"chat_{self.convo_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        if not await self.user_can_access_conversation(self.rm_id, self.convo_id):
            await self.close()
            return

        await self.accept()



    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            f"chat_{self.convo_id}",
            self.channel_name
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"]
        }))


    async def message_status(self, event):
        await self.send(text_data=json.dumps({
            "type": "message_status",
            "message_id": event["message_id"],
            "status": event["status"],
        }))

    @database_sync_to_async
    def user_can_access_conversation(self, rm_id, convo_id):
        return Conversation.objects.filter(
            id=convo_id,
            rm_id=rm_id
        ).exists()


# Visitor Live Chat Consumers

class VisitorConsumer(AsyncWebsocketConsumer):

    SLOW_RESPONSE_TIMEOUT = 30  # seconds — spec §6

    async def connect(self):
        self.session_key = self.scope["url_route"]["kwargs"]["session_key"]
        self.group_name = f"visitor_{self.session_key}"
        self._tried_rm_ids = set()
        self._reassign_task = None

        exists = await self.visitor_session_exists(self.session_key)
        if not exists:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Mark visitor online
        await self.set_visitor_online(self.session_key, True)

        # Notify RM inbox that visitor is online
        await self.notify_rm_inbox(self.session_key)

        # Notify RM inbox in real-time that visitor came online
        info = await self.get_rm_and_convo(self.session_key)
        if info:
            rm_id, convo_id = info
            self._tried_rm_ids.add(rm_id)
            await self.channel_layer.group_send(
                f"visitor_inbox_rm_{rm_id}",
                {
                    "type": "visitor_status_change",
                    "conversation_id": convo_id,
                    "is_online": True,
                }
            )
            # Spec §6 — start 30-s slow-response timer
            self._schedule_slow_response(convo_id, rm_id)

    async def disconnect(self, close_code):
        # Cancel pending slow-response task before cleanup
        if self._reassign_task and not self._reassign_task.done():
            self._reassign_task.cancel()

        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        # Mark visitor offline + mark open conversation as missed if no RM response yet
        await self.set_visitor_online(self.session_key, False)
        await self.mark_missed_if_unanswered(self.session_key)

        # Notify RM inbox in real-time that visitor went offline
        info = await self.get_rm_and_convo(self.session_key)
        if info:
            rm_id, convo_id = info
            await self.channel_layer.group_send(
                f"visitor_inbox_rm_{rm_id}",
                {
                    "type": "visitor_status_change",
                    "conversation_id": convo_id,
                    "is_online": False,
                }
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type == "message":
            await self.handle_visitor_message(data)
        elif msg_type == "heartbeat":
            await self.update_visitor_time(self.session_key, data.get("elapsed", 0))
        elif msg_type == "page_view":
            url   = data.get("url", "")
            title = data.get("title", "")
            await self.record_page_view(self.session_key, url, title, data.get("prev_duration", 0))
            # Push current page update to RM in real-time
            info = await self.get_rm_and_convo(self.session_key)
            if info:
                rm_id, convo_id = info
                await self.channel_layer.group_send(
                    f"visitor_inbox_rm_{rm_id}",
                    {
                        "type": "visitor_page_change",
                        "conversation_id": convo_id,
                        "current_page": url,
                        "page_title": title,
                    }
                )
        elif msg_type == "read_receipt":
            await self.handle_read_receipt(data)
        elif msg_type == "identify":
            await self.update_visitor_identity(
                self.session_key,
                data.get("name"),
                data.get("email"),
                data.get("phone")
            )

    async def handle_visitor_message(self, data):
        body = data.get("body", "").strip()
        if not body:
            return

        result = await self.save_visitor_message(self.session_key, body)
        if not result:
            return

        msg, convo = result

        # Echo back to visitor (with id and timestamp)
        await self.send(text_data=json.dumps({
            "type": "message_sent",
            "message": {
                "id": msg.id,
                "body": msg.body,
                "direction": "visitor",
                "time": localtime(msg.created_at).strftime("%I:%M %p"),
            }
        }))

        # Fallback if no RM is online — send greeting + quick-send buttons
        rm_online = await self.any_rm_online()
        if not rm_online:
            await self.trigger_fallback(convo.id)

        # Forward to RM chat group
        if convo.rm_id:
            await self.channel_layer.group_send(
                f"visitor_chat_{convo.id}",
                {
                    "type": "visitor_chat_message",
                    "message": {
                        "id": msg.id,
                        "conversation_id": convo.id,
                        "body": msg.body,
                        "direction": "visitor",
                        "message_type": "text",
                        "time": localtime(msg.created_at).strftime("%I:%M %p"),
                        "date": localtime(msg.created_at).strftime("%Y-%m-%d"),
                    }
                }
            )

            # Update RM inbox
            visitor = await self.get_visitor(self.session_key)
            await self.channel_layer.group_send(
                f"visitor_inbox_rm_{convo.rm_id}",
                {
                    "type": "visitor_inbox_update",
                    "conversation_id": convo.id,
                    "visitor_name": visitor.name or visitor.email or visitor.ip_address,
                    "preview": body[:80],
                    "unread": convo.unread_count_rm,
                    "direction": "visitor",
                    "time": msg.created_at.isoformat(),
                    "notify": True,
                }
            )

    async def handle_read_receipt(self, data):
        """Visitor has read RM messages — save to DB + notify RM chat socket."""
        message_ids = data.get("message_ids", [])
        if not message_ids:
            return
        await self.mark_messages_read(message_ids)
        convo_id = await self.get_open_convo_id(self.session_key)
        if convo_id:
            await self.channel_layer.group_send(
                f"visitor_chat_{convo_id}",
                {"type": "visitor_read_receipt", "message_ids": message_ids}
            )

    # Event handlers (messages pushed from RM side)

    async def visitor_rm_message(self, event):
        """RM sent a message — forward to visitor browser."""
        await self.send(text_data=json.dumps({
            "type": "rm_message",
            "message": event["message"]
        }))

    async def visitor_rm_joined(self, event):
        """RM joined the conversation."""
        await self.send(text_data=json.dumps({
            "type": "rm_joined",
            "rm_name": event["rm_name"]
        }))

    async def visitor_conversation_closed(self, event):
        await self.send(text_data=json.dumps({"type": "conversation_closed"}))

    # DB helpers

    @database_sync_to_async
    def visitor_session_exists(self, session_key):
        return VisitorSession.objects.filter(session_key=session_key).exists()

    @database_sync_to_async
    def get_open_convo_id(self, session_key):
        convo = VisitorConversation.objects.filter(
            visitor__session_key=session_key,
            status__in=["waiting", "active"]
        ).values_list("id", flat=True).first()
        return convo

    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        VisitorMessage.objects.filter(id__in=message_ids, direction="rm").update(is_read=True)

    @database_sync_to_async
    def get_visitor(self, session_key):
        return VisitorSession.objects.select_related("assigned_rm").get(session_key=session_key)

    @database_sync_to_async
    def set_visitor_online(self, session_key, is_online):
        VisitorSession.objects.filter(session_key=session_key).update(
            is_online=is_online, last_seen_at=timezone.now()
        )

    @database_sync_to_async
    def update_visitor_time(self, session_key, elapsed):
        from django.db.models import F
        VisitorSession.objects.filter(session_key=session_key).update(
            total_time_seconds=F("total_time_seconds") + elapsed,
            last_seen_at=timezone.now(),
            is_online=True
        )

    @database_sync_to_async
    def record_page_view(self, session_key, url, title, prev_duration):
        from django.db.models import F
        try:
            visitor = VisitorSession.objects.get(session_key=session_key)
            # Close previous open page view
            if prev_duration > 0:
                from RMPortal.models import VisitorPageView as PV
                last = PV.objects.filter(visitor=visitor, left_at__isnull=True).last()
                if last:
                    last.left_at = timezone.now()
                    last.duration_seconds = prev_duration
                    last.save(update_fields=["left_at", "duration_seconds"])
            # Create new page view
            from RMPortal.models import VisitorPageView as PV
            PV.objects.create(visitor=visitor, url=url, page_title=title)
            visitor.page_count = F("page_count") + 1
            visitor.current_page = url
            visitor.save(update_fields=["page_count", "current_page"])
        except VisitorSession.DoesNotExist:
            pass

    @database_sync_to_async
    def update_visitor_identity(self, session_key, name, email, phone):
        update = {}
        if name:
            update["name"] = name
        if email:
            update["email"] = email
        if phone:
            update["phone"] = phone
        if update:
            VisitorSession.objects.filter(session_key=session_key).update(**update)

    @database_sync_to_async
    def save_visitor_message(self, session_key, body):
        from django.db import transaction
        from .services import assign_or_fallback, pick_rm_for_visitor
        try:
            visitor = VisitorSession.objects.select_related("assigned_rm").get(session_key=session_key)
            with transaction.atomic():
                convo = (
                    VisitorConversation.objects
                    .filter(visitor=visitor, status__in=["waiting", "active"])
                    .select_for_update()
                    .first()
                )

                # If convo exists but its RM is now offline, hand off —
                # BUT only for waiting chats (RM never replied).
                # Active chats (RM already replied) stay pinned to that RM
                # even when they go offline; reassigning would break an
                # ongoing conversation.
                if convo and convo.rm_id and convo.status != "active":
                    if not (convo.rm and convo.rm.is_active and convo.rm.active_visitor_chat):
                        from .services import reassign_convo_to_new_rm
                        new_rm = pick_rm_for_visitor(visitor)
                        if new_rm and new_rm.id != convo.rm_id:
                            convo = reassign_convo_to_new_rm(convo, new_rm)

                # No open convo — re-assign or send WhatsApp fallback
                if not convo:
                    _rm, convo = assign_or_fallback(visitor)
                    if not convo:
                        return None

                msg = VisitorMessage.objects.create(
                    conversation=convo,
                    direction="visitor",
                    body=body
                )

                now = timezone.now()
                update_fields = [
                    "last_message_at", "last_message_preview", "last_message_direction",
                    "unread_count_rm"
                ]
                convo.last_message_at = now
                convo.last_message_preview = body[:100]
                convo.last_message_direction = "visitor"
                convo.unread_count_rm += 1

                if not convo.visitor_first_message_at:
                    convo.visitor_first_message_at = now
                    update_fields.append("visitor_first_message_at")

                # NOTE: visitor messages NEVER flip status to "active".
                # Only an RM reply can activate the conversation.
                convo.save(update_fields=update_fields)
            return msg, convo
        except VisitorSession.DoesNotExist:
            return None

    @database_sync_to_async
    def mark_missed_if_unanswered(self, session_key):
        """
        Spec §8 — on visitor disconnect, classify any waiting conversation:
          quickly_left   — visitor was on site <= 5s (wallclock)
          rm_no_reply    — visitor stayed >5s, had typed, RM never replied
          visitor_no_msg — visitor stayed >5s, never typed
        """
        try:
            visitor = VisitorSession.objects.get(session_key=session_key)
        except VisitorSession.DoesNotExist:
            return

        now = timezone.now()

        # Use wallclock (now - first_seen_at) as the source of truth for
        # "how long was the visitor on site?". total_time_seconds depends on
        # heartbeat pings that may not have fired yet for a fast-leaving
        # visitor, so it under-reports. Take the max of both to be safe.
        duration_sec = 0
        if visitor.first_seen_at:
            duration_sec = int((now - visitor.first_seen_at).total_seconds())
        duration_sec = max(duration_sec, visitor.total_time_seconds or 0)

        if duration_sec <= 5:
            reason = "quickly_left"
        else:
            reason = None  # decided per convo below

        open_convos = VisitorConversation.objects.filter(
            visitor=visitor,
            status="waiting",
            rm_first_response_at__isnull=True,
        )
        for convo in open_convos:
            if reason == "quickly_left":
                convo_reason = "quickly_left"
            elif convo.visitor_first_message_at:
                convo_reason = "rm_no_reply"
            else:
                convo_reason = "visitor_no_msg"

            convo.status = "missed"
            convo.missed_reason = convo_reason
            convo.closed_at = now
            convo.save(update_fields=["status", "missed_reason", "closed_at"])

            if convo.rm_id:
                try:
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    async_to_sync(get_channel_layer().group_send)(
                        f"visitor_inbox_rm_{convo.rm_id}",
                        {
                            "type": "visitor_inbox_update",
                            "conversation_id": convo.id,
                            "visitor_name": visitor.name or visitor.email or visitor.ip_address,
                            "preview": convo.last_message_preview,
                            "unread": convo.unread_count_rm,
                            "direction": convo.last_message_direction,
                            "time": (convo.last_message_at or now).isoformat(),
                            "notify": False,
                            "status": "missed",
                            "missed_reason": convo_reason,
                        },
                    )
                except Exception as e:
                    print("visitor_inbox_update on disconnect failed:", e)

    @database_sync_to_async
    def any_rm_online(self):
        from dashboard.models import RM as RMModel
        return RMModel.objects.filter(is_active=True, active_visitor_chat=True).exists()

    @database_sync_to_async
    def trigger_fallback(self, convo_id):
        from .services import send_visitor_fallback_message
        try:
            convo = VisitorConversation.objects.select_related("visitor").get(id=convo_id)
            # Don't send fallback if RM already responded — visitor has an active chat
            if convo.rm_first_response_at is None:
                send_visitor_fallback_message(convo)
        except VisitorConversation.DoesNotExist:
            pass

    async def visitor_fallback_options(self, event):
        """Forward WhatsApp quick-send buttons to the visitor widget."""
        await self.send(text_data=json.dumps({
            "type": "fallback_options",
            "options": event["options"],
        }))

    @database_sync_to_async
    def get_rm_and_convo(self, session_key):
        try:
            visitor = VisitorSession.objects.select_related("assigned_rm").get(session_key=session_key)
            if not visitor.assigned_rm_id:
                return None
            convo = VisitorConversation.objects.filter(
                visitor=visitor, status__in=["waiting", "active"]
            ).values_list("id", flat=True).last()
            if not convo:
                return None
            return visitor.assigned_rm_id, convo
        except VisitorSession.DoesNotExist:
            return None

    @database_sync_to_async
    def notify_rm_inbox(self, session_key):
        """When visitor connects, alert the assigned RM's inbox."""
        try:
            visitor = VisitorSession.objects.select_related("assigned_rm").get(session_key=session_key)
            if not visitor.assigned_rm_id:
                return None
            convo = VisitorConversation.objects.filter(
                visitor=visitor, status__in=["waiting", "active"]
            ).last()
            return visitor, convo
        except VisitorSession.DoesNotExist:
            return None

    # Spec §6 — 30-second slow-response auto-reassign chain

    def _schedule_slow_response(self, convo_id, rm_id):
        """Schedule a check `SLOW_RESPONSE_TIMEOUT` seconds from now."""
        if self._reassign_task and not self._reassign_task.done():
            self._reassign_task.cancel()
        self._reassign_task = asyncio.ensure_future(
            self._check_slow_response(convo_id, rm_id)
        )

    async def _check_slow_response(self, convo_id, rm_id):
        try:
            await asyncio.sleep(self.SLOW_RESPONSE_TIMEOUT)
        except asyncio.CancelledError:
            return

        # If RM has replied or convo changed state, nothing to do.
        still_waiting = await self._convo_still_waiting(convo_id)
        if not still_waiting:
            return

        # Mark current convo missed/slow_response and notify old RM's inbox.
        await self._mark_slow_response(convo_id, rm_id)

        # Try the next RM in the chain, excluding everyone we already tried.
        result = await self._reassign_to_next_rm(self.session_key, list(self._tried_rm_ids))
        if not result:
            # Exhausted — send fallback once and clear visitor's assigned RM.
            await self._exhaust_fallback(self.session_key)
            return

        new_rm_id, new_convo_id = result
        self._tried_rm_ids.add(new_rm_id)
        # Chain the next timer
        self._schedule_slow_response(new_convo_id, new_rm_id)

    @database_sync_to_async
    def _convo_still_waiting(self, convo_id):
        return VisitorConversation.objects.filter(
            id=convo_id,
            status="waiting",
            rm_first_response_at__isnull=True,
        ).exists()

    @database_sync_to_async
    def _mark_slow_response(self, convo_id, old_rm_id):
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        now = timezone.now()
        VisitorConversation.objects.filter(id=convo_id).update(
            status="missed",
            missed_reason="slow_response",
            closed_at=now,
        )
        if old_rm_id:
            try:
                async_to_sync(get_channel_layer().group_send)(
                    f"visitor_inbox_rm_{old_rm_id}",
                    {
                        "type": "visitor_inbox_update",
                        "conversation_id": convo_id,
                        "status": "missed",
                        "missed_reason": "slow_response",
                        "notify": False,
                        "preview": "",
                        "unread": 0,
                        "time": now.isoformat(),
                    },
                )
            except Exception as e:
                print("slow_response inbox notify failed:", e)

    @database_sync_to_async
    def _reassign_to_next_rm(self, session_key, exclude_ids):
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        from .services import assign_rm_for_visitor

        try:
            visitor = VisitorSession.objects.get(session_key=session_key)
        except VisitorSession.DoesNotExist:
            return None

        new_rm = assign_rm_for_visitor(exclude_ids=exclude_ids)
        if not new_rm:
            return None

        new_convo = VisitorConversation.objects.create(
            visitor=visitor,
            rm=new_rm,
            status="waiting",
        )
        visitor.assigned_rm = new_rm
        visitor.save(update_fields=["assigned_rm"])

        try:
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
                    "current_page": visitor.current_page or "",
                    "is_returning": visitor.is_returning,
                },
            )
        except Exception as e:
            print("visitor_new_session notify failed:", e)

        return new_rm.id, new_convo.id

    @database_sync_to_async
    def _exhaust_fallback(self, session_key):
        """All RMs tried — push the static WhatsApp-link auto-reply once and
        clear visitor.assigned_rm."""
        from .services import send_visitor_fallback_message
        try:
            visitor = VisitorSession.objects.get(session_key=session_key)
        except VisitorSession.DoesNotExist:
            return
        convo = (
            VisitorConversation.objects
            .filter(visitor=visitor)
            .order_by("-created_at")
            .first()
        )
        if convo and not convo.fallback_sent and convo.rm_first_response_at is None:
            send_visitor_fallback_message(convo)
            convo.fallback_sent = True
            convo.save(update_fields=["fallback_sent"])
            visitor.assigned_rm = None
            visitor.save(update_fields=["assigned_rm"])


class VisitorInboxConsumer(AsyncWebsocketConsumer):
    # rm_id -> scheduled offline task. Page refresh closes & reopens the
    # socket within a second, so delay the offline flip and cancel it if
    # the RM reconnects within the grace window.
    _pending_offline = {}
    _OFFLINE_GRACE_SECONDS = 15

    async def connect(self):
        self.rm_id = self.scope["session"].get("rm_id")
        if not self.rm_id:
            await self.close()
            return

        # Reconnect / refresh: cancel any pending offline task for this RM
        pending = self._pending_offline.pop(self.rm_id, None)
        if pending and not pending.done():
            pending.cancel()

        self.group_name = f"visitor_inbox_rm_{self.rm_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        # Don't flip offline immediately — a page refresh would lose our RM.
        # Schedule it for later; connect() cancels the task on reconnect.
        rm_id = getattr(self, "rm_id", None)
        if rm_id:
            existing = self._pending_offline.get(rm_id)
            if existing and not existing.done():
                existing.cancel()
            self._pending_offline[rm_id] = asyncio.create_task(
                self._delayed_mark_offline(rm_id)
            )

    async def _delayed_mark_offline(self, rm_id):
        try:
            await asyncio.sleep(self._OFFLINE_GRACE_SECONDS)
            await self.mark_rm_offline_and_reassign(rm_id)
        except asyncio.CancelledError:
            return
        finally:
            if self._pending_offline.get(rm_id) is asyncio.current_task():
                self._pending_offline.pop(rm_id, None)

    @database_sync_to_async
    def mark_rm_offline_and_reassign(self, rm_id):
        from dashboard.models import RM as RMModel
        from .services import reassign_rm_conversations
        try:
            rm = RMModel.objects.get(id=rm_id)
        except RMModel.DoesNotExist:
            return
        if not rm.active_visitor_chat:
            return
        rm.active_visitor_chat = False
        rm.save(update_fields=["active_visitor_chat"])
        reassign_rm_conversations(rm)

    async def receive(self, text_data):
        """Handle heartbeat pings from frontend to keep connection alive."""
        data = json.loads(text_data)
        if data.get("type") == "ping":
            await self._touch_heartbeat(self.rm_id)
            await self.send(text_data=json.dumps({"type": "pong"}))

    @database_sync_to_async
    def _touch_heartbeat(self, rm_id):
        """Spec §10 — WS ping updates last_heartbeat on the active login row."""
        from dashboard.models import RMLoginHistory
        RMLoginHistory.objects.filter(rm_id=rm_id, status=True).update(
            last_heartbeat=timezone.now()
        )

    async def visitor_inbox_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "visitor_inbox_update",
            "conversation_id": event["conversation_id"],
            "visitor_name": event.get("visitor_name"),
            "preview": event.get("preview"),
            "unread": event.get("unread", 0),
            "direction": event.get("direction"),
            "time": event.get("time"),
            "notify": event.get("notify", False),
            "status": event.get("status"),
            "missed_reason": event.get("missed_reason"),
        }))

    async def visitor_status_change(self, event):
        await self.send(text_data=json.dumps({
            "type": "visitor_status_change",
            "conversation_id": event["conversation_id"],
            "is_online": event["is_online"],
        }))

    async def visitor_page_change(self, event):
        await self.send(text_data=json.dumps({
            "type": "visitor_page_change",
            "conversation_id": event["conversation_id"],
            "current_page": event["current_page"],
            "page_title": event.get("page_title", ""),
        }))

    async def visitor_new_session(self, event):
        """Notification that a new visitor just landed on the site."""
        await self.send(text_data=json.dumps({
            "type": "visitor_new_session",
            "session_key": event["session_key"],
            "conversation_id": event.get("conversation_id"),
            "visitor_name": event.get("visitor_name"),
            "ip": event.get("ip"),
            "country": event.get("country"),
            "city": event.get("city"),
            "device_type": event.get("device_type"),
            "current_page": event.get("current_page"),
            "is_returning": event.get("is_returning", False),
            "notify": True,
        }))

    async def visitor_removed(self, event):
        """Conversation was reassigned away from this RM."""
        await self.send(text_data=json.dumps({
            "type": "visitor_removed",
            "conversation_id": event["conversation_id"],
        }))


class VisitorChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for RM chatting with a specific visitor.
    Group: visitor_chat_{convo_id}
    RM sends messages → saved to DB → forwarded to visitor group.
    """

    async def connect(self):
        self.rm_id = self.scope["session"].get("rm_id")
        self.convo_id = self.scope["url_route"]["kwargs"]["convo_id"]

        if not self.rm_id:
            await self.close()
            return

        if not await self.rm_can_access(self.rm_id, self.convo_id):
            await self.close()
            return

        self.group_name = f"visitor_chat_{self.convo_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get("type") == "message":
            body = data.get("body", "").strip()
            if body:
                await self.handle_rm_message(body)

    async def handle_rm_message(self, body):
        result = await self.save_rm_message(self.rm_id, self.convo_id, body)
        if not result:
            return

        msg, convo, session_key, rm_name = result

        msg_data = {
            "id": msg.id,
            "conversation_id": convo.id,
            "body": msg.body,
            "direction": "rm",
            "message_type": "text",
            "time": localtime(msg.created_at).strftime("%I:%M %p"),
            "date": localtime(msg.created_at).strftime("%Y-%m-%d"),
        }

        # Broadcast to RM chat group (so other RM tabs update too)
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "visitor_chat_message", "message": msg_data}
        )

        # Forward to visitor
        await self.channel_layer.group_send(
            f"visitor_{session_key}",
            {"type": "visitor_rm_message", "message": msg_data}
        )

        # Update RM inbox
        await self.channel_layer.group_send(
            f"visitor_inbox_rm_{self.rm_id}",
            {
                "type": "visitor_inbox_update",
                "conversation_id": convo.id,
                "visitor_name": convo.visitor.name or convo.visitor.email or convo.visitor.ip_address,
                "preview": body[:80],
                "unread": 0,
                "direction": "rm",
                "time": msg.created_at.isoformat(),
                "notify": False,
                "status": "active",
            }
        )

    # Event handlers

    async def visitor_chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "visitor_chat_message",
            "message": event["message"]
        }))

    async def visitor_read_receipt(self, event):
        await self.send(text_data=json.dumps({
            "type": "visitor_read",
            "message_ids": event["message_ids"]
        }))

    # DB helpers

    @database_sync_to_async
    def rm_can_access(self, rm_id, convo_id):
        return VisitorConversation.objects.filter(id=convo_id, rm_id=rm_id).exists()

    @database_sync_to_async
    def save_rm_message(self, rm_id, convo_id, body):
        from django.db import transaction
        try:
            with transaction.atomic():
                convo = (
                    VisitorConversation.objects
                    .select_related("visitor", "rm")
                    .select_for_update()
                    .get(id=convo_id, rm_id=rm_id)
                )

                msg = VisitorMessage.objects.create(
                    conversation=convo,
                    direction="rm",
                    body=body
                )

                now = timezone.now()
                update_fields = [
                    "last_message_at", "last_message_preview",
                    "last_message_direction", "unread_count_visitor"
                ]
                convo.last_message_at = now
                convo.last_message_preview = body[:100]
                convo.last_message_direction = "rm"
                convo.unread_count_visitor += 1
                convo.unread_count_rm = 0

                if not convo.rm_first_response_at:
                    convo.rm_first_response_at = now
                    update_fields.append("rm_first_response_at")
                    if convo.visitor_first_message_at:
                        delta = (now - convo.visitor_first_message_at).seconds
                        convo.response_time_seconds = delta
                        update_fields.append("response_time_seconds")

                if convo.status == "waiting":
                    convo.status = "active"
                    update_fields.append("status")

                update_fields.append("unread_count_rm")
                convo.save(update_fields=update_fields)

            session_key = convo.visitor.session_key
            rm_name = convo.rm.rm_name if convo.rm else "RM"
            return msg, convo, session_key, rm_name
        except VisitorConversation.DoesNotExist:
            return None
