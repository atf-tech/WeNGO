from django.urls import path
from . import views
from .webhook import webhook

urlpatterns = [
    path('', views.rmportal_index, name='rmportal_index'),
    path("login/", views.rm_login, name="rm_login"),
    path("logout/", views.rm_logout, name="rm_logout"),
    path("transactions/", views.all_transaction, name="all_transaction"),
    path("rm_collection/", views.rm_collection, name="rm_collection"),
    path('rm_keepalive/', views.rm_keepalive, name='rm_keepalive'),
    path('keepalive/', views.rm_keepalive),

    path("webhook/", webhook, name="whatsapp_webhook"),

    # WhatsApp conversation endpoints
    path("conversation/<int:convo_id>/messages/", views.messages_partial, name="messages-partial"),
    path("conversation/<int:convo_id>/inactive/", views.mark_inactive),
    path("conversation/<int:convo_id>/active/", views.mark_active, name="mark_active"),
    path("conversation/<int:convo_id>/send/", views.send_message, name="send-message"),
    path("conversation/<int:convo_id>/send-media/", views.send_media_message, name="send-media-message"),

    # Visitor live chat — website-facing API
    path("visitor/session/init/", views.visitor_session_init, name="visitor_session_init"),
    path("visitor/identify/", views.visitor_identify, name="visitor_identify"),
    path("visitor/send/", views.visitor_send_message, name="visitor_send_message"),
    path("visitor/send-file/", views.visitor_send_file, name="visitor_send_file"),

    # Visitor conversation endpoints (RM side)
    path("visitor-conversation/<int:convo_id>/messages/", views.visitor_messages_partial, name="visitor-messages-partial"),
    path("visitor-conversation/<int:convo_id>/send/", views.visitor_send, name="visitor_send"),
    path("visitor-conversation/<int:convo_id>/send-file/", views.visitor_send_rm_file, name="visitor_send_rm_file"),
    path("visitor-conversation/<int:convo_id>/close/", views.visitor_close_conversation, name="visitor_close"),

    # RM status toggles (identified by rm_code slug)
    path("<str:rm_code>/whatsapp/status/", views.whatsapp_status_toggle, name="whatsapp_status_toggle"),
    path("<str:rm_code>/visitor/status/", views.visitor_chat_status_toggle, name="visitor_chat_status_toggle"),
    path("<str:rm_code>/visitor/force-offline/", views.visitor_force_offline, name="visitor_force_offline"),

    # RM Chat Page
    # path("webchat/", views.webchat, name="webchat"),
    path("<str:rm_code>/webchat/", views.whatsapp, name="webchat"),

    # <str:rm_code> patterns LAST (catches any rm_code)
    path("<str:rm_code>/gpay/payments/", views.rm_gpay_payments, name="rm_gpay_payments"),
    path("<str:rm_code>/collection/", views.rm_collection, name="rm_collection"),
    path("<str:rm_code>/", views.rmportal_index, name="rmportal_index"),
]
