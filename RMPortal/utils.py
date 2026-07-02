import subprocess
import uuid
import os
from datetime import time as dt_time, timezone as dt_timezone, timedelta
from django.conf import settings
from django.utils import timezone


IST = dt_timezone(timedelta(hours=5, minutes=30))
NIGHT_END = dt_time(9, 30)


def is_night_hours(now=None):
    now = now or timezone.now()
    now_ist = now.astimezone(IST)
    return now_ist.time() < NIGHT_END


def convert_webm_to_ogg(file_obj):
    tmp_dir = os.path.join(settings.MEDIA_ROOT, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    uid = uuid.uuid4().hex
    webm_path = os.path.join(tmp_dir, f"{uid}.webm")
    ogg_path = os.path.join(tmp_dir, f"{uid}.ogg")

    with open(webm_path, "wb") as out:
        if hasattr(file_obj, "chunks"):
            for chunk in file_obj.chunks():
                out.write(chunk)
        else:
            file_obj.open("rb")
            out.write(file_obj.read())
            file_obj.close()

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", webm_path,
            "-c:a", "copy",
            ogg_path,
        ],
        check=True,
    )

    return webm_path, ogg_path
