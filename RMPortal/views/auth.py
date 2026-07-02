from functools import wraps

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import F
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

from dashboard.models import RM, RMLoginHistory
from RMPortal.apps import RMPortalConfig


def _get_authenticated_rm(request):
    rm_id = request.session.get("rm_id")
    if not rm_id:
        return None

    rm = RM.objects.filter(id=rm_id, is_active=True).first()
    if not rm:
        return None

    record = RMLoginHistory.objects.filter(rm_id=rm.id, status=True).order_by("-login_time").first()
    if not record or record.logout_time:
        return None

    return rm


def rm_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        rm = _get_authenticated_rm(request)
        if not rm:
            request.session.flush()
            return redirect("rm_login")

        request.rm = rm
        request.rm_id = rm.id

        rm_code = kwargs.get("rm_code")
        if rm_code and getattr(rm, "rm_code", None) != rm_code:
            return redirect("webchat", rm_code=rm.rm_code)

        return view_func(request, *args, **kwargs)

    return wrapper


def rm_keepalive(request):
    rm_id = request.session.get("rm_id")
    if not rm_id:
        request.session.flush()
        return JsonResponse({"status": "expired"}, status=401)

    now = timezone.now()
    RMLoginHistory.objects.filter(rm_id=rm_id, status=True).update(last_heartbeat=now)

    with RMPortalConfig.lock:
        RMPortalConfig.last_seen[rm_id] = now

    request.session.set_expiry(3600)
    return JsonResponse({"status": "alive"})


def rm_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password", "").strip()

        rm = RM.objects.filter(rm_email__iexact=username, is_active=True).first()
        if rm and rm.rm_password:
            if rm.rm_password.startswith(('pbkdf2_', 'argon2', 'bcrypt')):
                password_ok = check_password(password, rm.rm_password)
            else:
                password_ok = (password == rm.rm_password)
                if password_ok:
                    rm.rm_password = make_password(password)
                    rm.save(update_fields=['rm_password'])
        else:
            password_ok = False

        if not password_ok:
            return redirect("rm_login")

        old_rm_id = request.session.get("rm_id")
        if old_rm_id and old_rm_id != rm.id:
            RMLoginHistory.objects.filter(rm_id=old_rm_id, status=True).update(
                logout_time=timezone.now(),
                status=False,
                duration=timezone.now() - F("login_time"),
            )
        request.session.cycle_key()

        request.session["rm_id"] = rm.id
        request.session["rm_code"] = rm.rm_code
        request.session.set_expiry(3600)

        now = timezone.now()
        RMLoginHistory.objects.create(
            rm=rm, login_time=now, status=True, last_heartbeat=now
        )

        with RMPortalConfig.lock:
            RMPortalConfig.last_seen[rm.id] = now

        return redirect("webchat", rm_code=rm.rm_code)

    return render(request, "rm_login.html")


def rm_logout(request):
    rm_id = request.session.get("rm_id")
    if rm_id:
        RMLoginHistory.objects.filter(rm_id=rm_id, status=True).update(
            logout_time=timezone.now(),
            status=False,
            duration=timezone.now() - F("login_time"),
        )
    request.session.flush()
    return redirect("rm_login")
