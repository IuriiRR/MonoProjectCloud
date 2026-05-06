import json
import signal
import time
import urllib.request
from threading import Event
from typing import Any, Dict

from local_server.cloud_scheduler import SchedulerGateway
from local_server.config import Settings
from local_server.health import mark_error, mark_heartbeat


def _telegram_api(bot_token: str, method: str, body: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/{method}",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}


def _delete_webhook(settings: Settings) -> None:
    _telegram_api(settings.telegram_bot_token, "deleteWebhook", {"drop_pending_updates": False})


def _set_webhook(settings: Settings) -> None:
    body: Dict[str, Any] = {"url": settings.telegram_webhook_url}
    if settings.telegram_webhook_secret:
        body["secret_token"] = settings.telegram_webhook_secret
    _telegram_api(settings.telegram_bot_token, "setWebhook", body)


def unblock_cloud(gateway: SchedulerGateway, settings: Settings) -> None:
    gateway.resume_job(settings.cloud_sync_worker_job)
    gateway.resume_job(settings.cloud_daily_reports_job)
    gateway.run_job_now(settings.cloud_sync_worker_job)
    gateway.run_job_now(settings.cloud_daily_reports_job)
    _set_webhook(settings)
    gateway.pause_job(settings.cloud_unblocker_job)


def cede_to_local(gateway: SchedulerGateway, settings: Settings) -> None:
    gateway.pause_job(settings.cloud_sync_worker_job)
    gateway.pause_job(settings.cloud_daily_reports_job)
    _delete_webhook(settings)
    gateway.resume_job(settings.cloud_unblocker_job)
    gateway.push_job_forward(settings.cloud_unblocker_job, lead_seconds=settings.unblocker_lead_sec)


def start_control_loop(gateway: SchedulerGateway, settings: Settings) -> Event:
    stop_event = Event()

    def _handle_signal(_signum, _frame):
        try:
            unblock_cloud(gateway, settings)
        finally:
            stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    cede_to_local(gateway, settings)

    while not stop_event.is_set():
        try:
            gateway.push_job_forward(settings.cloud_unblocker_job, lead_seconds=settings.unblocker_lead_sec)
            mark_heartbeat()
        except Exception as e:
            mark_error(str(e))
        stop_event.wait(settings.heartbeat_interval_sec)

    return stop_event
