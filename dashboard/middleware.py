from django.utils.cache import add_never_cache_headers


class DashboardNoCacheMiddleware:
    """
    Prevent browser caching for all dashboard pages.
    Ensures dashboard pages are never viewable using browser Back after logout.
    Mirrors IPF's no-cache strategy.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Apply no-cache headers only to dashboard URLs
        if request.path.startswith("/dashboard/"):
            add_never_cache_headers(response)
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response

