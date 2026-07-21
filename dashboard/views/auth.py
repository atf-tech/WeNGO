from functools import wraps

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone


def _get_dashboard_user(request):
    """
    Get the authenticated dashboard superuser from session.
    Returns the User object if valid, None otherwise.
    Mirrors RMPortal's _get_authenticated_rm() pattern.
    """
    if not request.user.is_authenticated:
        return None

    if not request.user.is_superuser or not request.user.is_active:
        return None

    return request.user


def superuser_required(view_func=None, login_url=None):
    """
    Decorator that protects dashboard views.
    Only authenticated superusers can access.
    Mirrors RMPortal's rm_login_required pattern exactly.

    If not authenticated, session is flushed and user is redirected to login.

    Can be used with or without arguments:
        @superuser_required
        @superuser_required(login_url='/dashboard/login')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = _get_dashboard_user(request)
            if not user:
                logout(request)
                request.session.flush()
                return redirect(login_url or "dashboard_login")

            request.dashboard_user = user
            return func(request, *args, **kwargs)
        return wrapper

    if view_func is not None:
        return decorator(view_func)

    return decorator


def dashboard_login(request):
    """
    Dashboard login view.
    Uses Django authenticate() + login() like a standard Django auth flow.
    Only Django superusers (is_superuser=True) are allowed.
    Mirrors RMPortal's rm_login() pattern.

    - authenticate(username, password)
    - verify user.is_superuser == True
    - If not superuser, show invalid login
    - On success: call Django login(), cycle_key(), set_expiry(300)
    - Redirect to /dashboard/
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_superuser and user.is_active:
            # Cycle session key for security (same as rm_login)
            request.session.cycle_key()

            # Call Django login to create authenticated session
            login(request, user)

            # Set session timeout to 5 minutes (300 seconds) like IPF
            request.session.set_expiry(300)

            return redirect("home")
        else:
            if user is not None and not user.is_superuser:
                messages.error(
                    request,
                    "Invalid login credentials.",
                )
            else:
                messages.error(request, "Invalid login credentials.")

        return redirect("dashboard_login")

    return render(request, "dashboard/dashboard_login.html")


def dashboard_logout(request):
    """
    Logout the dashboard user and redirect to login page.
    Mirrors RMPortal's rm_logout() pattern.
    """
    logout(request)
    request.session.flush()
    return redirect("dashboard_login")


def dashboard_keepalive(request):
    """
    Keepalive endpoint for dashboard session.
    Refreshes session expiry while user is active.
    Mirrors RMPortal's rm_keepalive() pattern.

    Returns JSON:
    - {"status": "alive"} if session is valid
    - {"status": "expired"} if session is expired
    """
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"status": "expired"}, status=401)

    # Refresh session expiry (5 minutes from now)
    request.session.set_expiry(300)

    return JsonResponse({"status": "alive"})
