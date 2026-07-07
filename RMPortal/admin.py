from django.contrib import admin
from .models import (
    Donor,
    Conversation,
    Message,
    MessageMedia,
    VisitorSession,
    VisitorPageView,
    VisitorConversation,
    VisitorMessage,
)

admin.site.register(Donor)
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(MessageMedia)
admin.site.register(VisitorSession)
admin.site.register(VisitorPageView)
admin.site.register(VisitorConversation)
admin.site.register(VisitorMessage)
