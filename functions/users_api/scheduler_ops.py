import json
import os
from datetime import datetime
from typing import Any, Dict

from google.cloud import scheduler_v1


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _project_id() -> str:
    project_id = _env("FIRESTORE_PROJECT_ID") or _env("GOOGLE_CLOUD_PROJECT") or _env("GCP_PROJECT")
    if not project_id:
        raise ValueError("Missing GCP project id (FIRESTORE_PROJECT_ID/GOOGLE_CLOUD_PROJECT/GCP_PROJECT)")
    return project_id


def _scheduler_region() -> str:
    return _env("GCP_SCHEDULER_REGION", "europe-west1")


def _job_path(job_name: str) -> str:
    return f"projects/{_project_id()}/locations/{_scheduler_region()}/jobs/{job_name}"


def _scheduler_client() -> scheduler_v1.CloudSchedulerClient:
    return scheduler_v1.CloudSchedulerClient()


def pause_job(job_name: str) -> None:
    _scheduler_client().pause_job(name=_job_path(job_name))


def resume_job(job_name: str) -> None:
    _scheduler_client().resume_job(name=_job_path(job_name))


def run_job_now(job_name: str) -> None:
    _scheduler_client().run_job(name=_job_path(job_name))


def _telegram_api(bot_token: str, method: str, body: Dict[str, Any]) -> Any:
    import urllib.error
    import urllib.request

    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/{method}",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise ValueError(f"Telegram API {method} failed with HTTP {e.code}: {raw}") from e


def set_telegram_webhook() -> str:
    token = _env("TELEGRAM_BOT_TOKEN")
    webhook_url = _env("TELEGRAM_WEBHOOK_URL")
    if not token or not webhook_url:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_WEBHOOK_URL")

    payload: Dict[str, Any] = {"url": webhook_url}
    secret = _env("TELEGRAM_WEBHOOK_SECRET")
    if secret:
        payload["secret_token"] = secret

    result = _telegram_api(token, "setWebhook", payload) or {}
    if not bool(result.get("ok")):
        raise ValueError(f"setWebhook failed: {result}")
    return str(result.get("description") or "ok")


def unblock_cloud_jobs() -> Dict[str, Any]:
    sync_worker_job = _env("CLOUD_SYNC_WORKER_JOB", "sync-worker-hourly")
    daily_reports_job = _env("CLOUD_DAILY_REPORTS_JOB", "daily-reports-daily")
    unblocker_job = _env("CLOUD_UNBLOCKER_JOB", "rpi-unblocker")

    actions: list[str] = []
    warnings: list[str] = []

    for job in (sync_worker_job,):
        try:
            resume_job(job)
            actions.append(f"resumed:{job}")
        except Exception as e:
            warnings.append(f"resume_failed:{job}:{e}")

    for job in (sync_worker_job,):
        try:
            run_job_now(job)
            actions.append(f"run_now:{job}")
        except Exception as e:
            warnings.append(f"run_now_failed:{job}:{e}")

    try:
        description = set_telegram_webhook()
        actions.append(f"set_webhook:{description}")
    except Exception as e:
        warnings.append(f"set_webhook_failed:{e}")

    try:
        pause_job(unblocker_job)
        actions.append(f"paused:{unblocker_job}")
    except Exception as e:
        warnings.append(f"pause_failed:{unblocker_job}:{e}")

    return {"actions": actions, "warnings": warnings}
