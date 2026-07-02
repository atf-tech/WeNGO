from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from dashboard.models import RM, RMLoginHistory


def create_login_record(rm):
    """Record a login event for the RM."""
    active = RMLoginHistory.objects.filter(rm=rm, status=True).last()
    if not active:
        RMLoginHistory.objects.create(rm=rm, login_time=timezone.now(), status=True)


def close_login_record(rm):
    """Record a logout event for the RM."""
    active = RMLoginHistory.objects.filter(rm=rm, status=True).last()
    if active:
        logout_time = timezone.now()
        active.logout_time = logout_time
        active.duration = logout_time - active.login_time
        active.status = False
        active.save()