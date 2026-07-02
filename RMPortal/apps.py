import os
import sys
import time
from threading import Thread, Lock
from datetime import timedelta

from django.apps import AppConfig
from django.utils import timezone


SKIP_ARGS = {
    "migrate", "makemigrations", "collectstatic", "test", "shell",
    "dbshell", "dumpdata", "loaddata", "createsuperuser", "changepassword",
    "showmigrations", "sqlmigrate", "check", "compilemessages",
    "makemessages", "flush", "inspectdb", "squashmigrations",
}

HEARTBEAT_CUTOFF_SECONDS = 60
SWEEP_INTERVAL_SECONDS = 30
STALE_SWEEP_INTERVAL_SECONDS = 30 * 60


def _should_start_background():
    if len(sys.argv) >= 2 and sys.argv[1] in SKIP_ARGS:
        return False
    if os.environ.get("RUN_MAIN") != "true" and "runserver" in sys.argv:
        return False
    return True


class RMPortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'RMPortal'

    last_seen = {}
    lock = Lock()

    _last_stale_sweep = 0.0

    def ready(self):
        if not _should_start_background():
            return

        Thread(target=self._heartbeat_sweep_loop, daemon=True).start()

    def _heartbeat_sweep_loop(self):
        from django.contrib.sessions.models import Session
        from dashboard.models import RMLoginHistory
        from RMPortal.services import (
            reassign_rm_conversations,
            force_all_rms_offline,
            expire_stale_waiting_conversations,
        )
        from RMPortal.utils import is_night_hours

        while True:
            try:
                now = timezone.now()

                Session.objects.filter(expire_date__lt=now).delete()

                if is_night_hours():
                    try:
                        force_all_rms_offline()
                    except Exception as e:
                        print("force_all_rms_offline failed:", e)

                cutoff = now - timedelta(seconds=HEARTBEAT_CUTOFF_SECONDS)
                stale = (
                    RMLoginHistory.objects
                    .filter(status=True, last_heartbeat__lt=cutoff)
                    .select_related("rm")
                )
                for record in stale:
                    record.logout_time = now
                    record.status = False
                    record.duration = now - record.login_time
                    record.save(update_fields=["logout_time", "status", "duration"])

                    rm = record.rm
                    if rm and rm.active_visitor_chat:
                        rm.active_visitor_chat = False
                        rm.save(update_fields=["active_visitor_chat"])
                        try:
                            reassign_rm_conversations(rm)
                        except Exception as e:
                            print("reassign_rm_conversations failed:", e)

                if (time.time() - RMPortalConfig._last_stale_sweep) >= STALE_SWEEP_INTERVAL_SECONDS:
                    try:
                        expire_stale_waiting_conversations()
                    except Exception as e:
                        print("expire_stale_waiting_conversations failed:", e)
                    RMPortalConfig._last_stale_sweep = time.time()

            except Exception as e:
                print("heartbeat sweep error:", e)

            time.sleep(SWEEP_INTERVAL_SECONDS)
