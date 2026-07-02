from django.db import models
from dashboard.models import RM



class Donor(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.phone_number





class Conversation(models.Model):
    donor = models.ForeignKey(
        Donor,
        on_delete=models.CASCADE,
        related_name="conversations"
    )

    rm = models.ForeignKey(
        RM,
        on_delete=models.CASCADE,
        related_name="conversations"
    )

    status = models.CharField(
        max_length=10,
        choices=[("open", "Open"), ("closed", "Closed")],
        default="open"
    )

    unread_count = models.PositiveIntegerField(default=0)

    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_preview = models.TextField(blank=True)
    last_message_type = models.CharField(max_length=10, null=True, blank=True)
    last_message_status = models.CharField(max_length=10, null=True, blank=True)
    last_message_direction = models.CharField(max_length=3, null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_seen_message_id = models.BigIntegerField(null=True, blank=True)




    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.donor.phone_number} → {self.rm.rm_name}"
    
    
    class Meta:
        indexes = [
            models.Index(fields=["rm", "status"]),
            models.Index(fields=["rm", "is_active"]),
            models.Index(fields=["last_message_at"]),
        ]






class Message(models.Model):
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("read", "Read"),
    ]

    MESSAGE_TYPE_CHOICES = [
        ("text", "Text"),
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("document", "Document"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        related_name="messages",
        on_delete=models.CASCADE
    )

    direction = models.CharField(
        max_length=3,
        choices=[("in", "Incoming"), ("out", "Outgoing")]
    )

    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPE_CHOICES,
        default="text"
    )

    body = models.TextField(blank=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="sent"
    )
    
    reply_to = models.ForeignKey(
    "self",
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="replies",
    db_index=True
)

    external_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["external_id"]),
        ]






class MessageMedia(models.Model):
    message = models.OneToOneField(
        Message,
        related_name="media",
        on_delete=models.CASCADE
    )

    file = models.FileField(upload_to="whatsapp_media/")
    mime_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()

    # WhatsApp Cloud media id
    wa_media_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)



# Visitor Live Chat Models

class VisitorSession(models.Model):
    DEVICE_CHOICES = [
        ("desktop", "Desktop"),
        ("mobile", "Mobile"),
        ("tablet", "Tablet"),
        ("unknown", "Unknown"),
    ]

    # Unique key per browser tab session; cookie_id persists across sessions
    session_key = models.CharField(max_length=64, unique=True, db_index=True)
    cookie_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    # Contact info — filled when visitor provides in chat
    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True, db_index=True)
    phone = models.CharField(max_length=20, null=True, blank=True, db_index=True)

    # IP & geo (from ip-api.com)
    ip_address = models.GenericIPAddressField(db_index=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    isp = models.CharField(max_length=200, null=True, blank=True)

    # Browser / device (parsed from User-Agent)
    user_agent = models.TextField(null=True, blank=True)
    browser = models.CharField(max_length=100, null=True, blank=True)
    os = models.CharField(max_length=100, null=True, blank=True)
    device_type = models.CharField(max_length=10, choices=DEVICE_CHOICES, default="unknown")

    # Traffic source
    referrer = models.CharField(max_length=500, null=True, blank=True)
    utm_source = models.CharField(max_length=100, null=True, blank=True)
    utm_medium = models.CharField(max_length=100, null=True, blank=True)
    utm_campaign = models.CharField(max_length=100, null=True, blank=True)

    # Time tracking
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    total_time_seconds = models.PositiveIntegerField(default=0)
    page_count = models.PositiveIntegerField(default=0)

    is_online = models.BooleanField(default=True)
    is_returning = models.BooleanField(default=False)
    current_page = models.CharField(max_length=500, null=True, blank=True)

    # Round-robin assignment
    assigned_rm = models.ForeignKey(
        RM,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_visitors"
    )

    def __str__(self):
        label = self.name or self.email or self.phone or self.ip_address
        return f"{label} ({self.session_key[:8]})"

    class Meta:
        indexes = [
            models.Index(fields=["ip_address"]),
            models.Index(fields=["first_seen_at"]),
            models.Index(fields=["is_online"]),
        ]


class VisitorPageView(models.Model):
    visitor = models.ForeignKey(
        VisitorSession,
        on_delete=models.CASCADE,
        related_name="page_views"
    )
    url = models.CharField(max_length=500)
    page_title = models.CharField(max_length=200, null=True, blank=True)
    entered_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["entered_at"]
        indexes = [
            models.Index(fields=["visitor", "entered_at"]),
        ]


class VisitorConversation(models.Model):
    STATUS_CHOICES = [
        ("waiting", "Waiting"),       # visitor online, waiting for RM
        ("active", "Active"),         # both sides messaging
        ("closed", "Closed"),         # ended normally (End Chat)
        ("missed", "Missed"),         # visitor left before RM responded
        ("reassigned", "Reassigned"), # visitor moved to another RM
    ]
    INITIATED_BY_CHOICES = [
        ("visitor", "Visitor"),
        ("rm", "RM"),
    ]

    # Spec §4 — full missed_reason taxonomy
    MISSED_REASON_CHOICES = [
        ("no_rm", "No RM available"),
        ("night_chat", "Night hours"),
        ("rm_no_reply", "RM did not reply"),
        ("visitor_no_msg", "Visitor left without typing"),
        ("quickly_left", "Visitor left within 5s"),
        ("stale_waiting", "Stale waiting"),
        ("slow_response", "RM did not reply in 30s"),
    ]

    visitor = models.ForeignKey(
        VisitorSession,
        on_delete=models.CASCADE,
        related_name="visitor_conversations"
    )
    rm = models.ForeignKey(
        RM,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visitor_conversations"
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="waiting")
    missed_reason = models.CharField(
        max_length=16,
        choices=MISSED_REASON_CHOICES,
        null=True,
        blank=True,
        db_index=True,
    )
    initiated_by = models.CharField(max_length=7, choices=INITIATED_BY_CHOICES, default="visitor")

    # Unread counts
    unread_count_rm = models.PositiveIntegerField(default=0)
    unread_count_visitor = models.PositiveIntegerField(default=0)

    # Inbox preview
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_preview = models.TextField(blank=True)
    last_message_direction = models.CharField(max_length=7, null=True, blank=True)

    # SLA / analytics
    visitor_first_message_at = models.DateTimeField(null=True, blank=True)
    rm_first_response_at = models.DateTimeField(null=True, blank=True)
    response_time_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Fallback auto-reply idempotency (spec §3 / §14)
    fallback_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        rm_name = self.rm.rm_name if self.rm else "Unassigned"
        return f"Visitor {self.visitor.session_key[:8]} → {rm_name} [{self.status}]"

    class Meta:
        indexes = [
            models.Index(fields=["rm", "status"]),
            models.Index(fields=["visitor"]),
            models.Index(fields=["last_message_at"]),
        ]


class VisitorMessage(models.Model):
    DIRECTION_CHOICES = [
        ("visitor", "Visitor to RM"),
        ("rm", "RM to Visitor"),
    ]
    MESSAGE_TYPE_CHOICES = [
        ("text", "Text"),
        ("image", "Image"),
        ("file", "File"),
    ]

    conversation = models.ForeignKey(
        VisitorConversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    direction = models.CharField(max_length=7, choices=DIRECTION_CHOICES)
    message_type = models.CharField(max_length=5, choices=MESSAGE_TYPE_CHOICES, default="text")
    body = models.TextField(blank=True)
    file = models.FileField(upload_to="visitor_media/", null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]
