from datetime import datetime

from django.utils.timezone import make_aware


def start_and_end_of_day(dt):
    start = make_aware(datetime.combine(dt, datetime.min.time()))
    end = make_aware(datetime.combine(dt, datetime.max.time()))
    return start, end


def _get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")