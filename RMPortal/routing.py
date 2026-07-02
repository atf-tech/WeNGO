from django.urls import re_path
from .consumers import (
    ChatConsumer, InboxConsumer,
    VisitorConsumer, VisitorInboxConsumer, VisitorChatConsumer,
)

websocket_urlpatterns = [
    # WhatsApp chat
    re_path(r"^ws/inbox/$", InboxConsumer.as_asgi()),
    re_path(r"^ws/chat/(?P<convo_id>\d+)/$", ChatConsumer.as_asgi()),

    # Visitor live chat
    re_path(r"^ws/visitor/(?P<session_key>[a-zA-Z0-9_-]+)/$", VisitorConsumer.as_asgi()),
    re_path(r"^ws/visitor-inbox/$", VisitorInboxConsumer.as_asgi()),
    re_path(r"^ws/visitor-chat/(?P<convo_id>\d+)/$", VisitorChatConsumer.as_asgi()),
]
