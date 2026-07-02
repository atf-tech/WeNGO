from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from dashboard.models import RM
from RMPortal.models import Conversation as WAConv, VisitorConversation 
from RMPortal.services import expire_stale_waiting_conversations
from .auth import rm_login_required


@rm_login_required
def inbox(request):
    return render(request, 'inbox.html', {"rm": request.rm})


@rm_login_required
def whatsapp_chat(request):
    rm = request.rm
    if not rm:
        return render(request, 'whatsapp_chat.html')

    

    conversations = (
        WAConv.objects
        .filter(rm=rm)
        .select_related("donor")
        .order_by("-last_message_at")[:50]
    )

    visitor_conversations = (
        VisitorConversation.objects
        .filter(rm=rm)
        .select_related("visitor")
        .order_by("-last_message_at")[:50]
    )

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    active_count = VisitorConversation.objects.filter(
        rm=rm, status="active", created_at__gte=today_start
    ).count()
    reassigned_count = VisitorConversation.objects.filter(
        rm=rm, status="reassigned", created_at__gte=today_start
    ).count()
    missed_count = VisitorConversation.objects.filter(
        rm=rm, status="missed", created_at__gte=today_start
    ).count()

    quickly_left_cutoff = now - timedelta(seconds=5)
    quickly_left_count = VisitorConversation.objects.filter(
        rm=rm, status="missed",
        missed_reason="quickly_left",
        created_at__gte=today_start,
    ).count()

    expired = expire_stale_waiting_conversations()

    context = {
        "rm": rm,
        "conversations": conversations,
        "visitor_conversations": visitor_conversations,
        "active_count": active_count,
        "reassigned_count": reassigned_count,
        "missed_count": missed_count,
        "quickly_left_count": quickly_left_count,
    }
    return render(request, 'whatsapp_chat.html', context)


@rm_login_required
def all_transaction(request):
    return render(request, 'all_transaction.html', {"rm": request.rm})



