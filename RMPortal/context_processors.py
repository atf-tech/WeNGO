from django.conf import settings


def rm_context(request):
    """Expose the active RM session data to RM Portal templates."""
    session = getattr(request, "session", None)
    rm_id = session.get("rm_id") if session else None
    rm_code = session.get("rm_code") if session else None

    rm = None
    if rm_id:
        try:
            from dashboard.models import RM
            rm = RM.objects.filter(id=rm_id).first()
        except Exception:
            rm = None

    return {
        "rm": rm,
        "rm_id": rm_id,
        "rm_code": rm_code,
        "LOGIN_URL": getattr(settings, "LOGIN_URL", "/rm/login"),
    }
