from django.utils import timezone
from RMPortal.apps import RMPortalConfig


class RMAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session = getattr(request, "session", None)
        request.rm_id = session.get("rm_id") if session else None
        return self.get_response(request)


class UpdateLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        rm_id = request.session.get("rm_id")
        if rm_id:
            with RMPortalConfig.lock:
                RMPortalConfig.last_seen[rm_id] = timezone.now()

        return response

