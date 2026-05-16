import os
from pydantic import BaseModel


class Settings(BaseModel):
    gcp_project_id: str
    gcp_scheduler_region: str = "europe-west1"
    cloud_unblocker_job: str = "rpi-unblocker"
    cloud_sync_worker_job: str = "sync-worker-hourly"
    cloud_daily_reports_job: str = "daily-reports-daily"

    users_api_url: str
    accounts_api_url: str
    transactions_api_url: str
    sync_worker_url: str = "http://127.0.0.1:8084"
    sync_worker_cloud_url: str = "http://127.0.0.1:8094"
    sync_transactions_url: str
    report_api_url: str = ""

    internal_api_key: str
    telegram_bot_token: str
    telegram_webhook_url: str
    telegram_webhook_secret: str = ""

    report_timezone: str = "Europe/Kyiv"
    sync_worker_cron: str = "0 18 * * *"
    cloud_backup_cron: str = "0 7 * * *"
    daily_reports_cron: str = "45 21 * * *"
    heartbeat_interval_sec: int = 600
    unblocker_lead_sec: int = 1800
    health_port: int = 9090


def load_settings() -> Settings:
    return Settings(
        gcp_project_id=(os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip(),
        gcp_scheduler_region=(os.getenv("GCP_SCHEDULER_REGION") or "europe-west1").strip(),
        cloud_unblocker_job=(os.getenv("CLOUD_UNBLOCKER_JOB") or "rpi-unblocker").strip(),
        cloud_sync_worker_job=(os.getenv("CLOUD_SYNC_WORKER_JOB") or "sync-worker-hourly").strip(),
        cloud_daily_reports_job=(os.getenv("CLOUD_DAILY_REPORTS_JOB") or "daily-reports-daily").strip(),
        users_api_url=(os.getenv("USERS_API_URL") or "").strip(),
        accounts_api_url=(os.getenv("ACCOUNTS_API_URL") or "").strip(),
        transactions_api_url=(os.getenv("TRANSACTIONS_API_URL") or "").strip(),
        sync_worker_url=(os.getenv("SYNC_WORKER_URL") or "http://127.0.0.1:8084").strip(),
        sync_worker_cloud_url=(os.getenv("SYNC_WORKER_CLOUD_URL") or "http://127.0.0.1:8094").strip(),
        sync_transactions_url=(os.getenv("SYNC_TRANSACTIONS_URL") or "").strip(),
        report_api_url=(os.getenv("REPORT_API_URL") or "").strip(),
        internal_api_key=(os.getenv("INTERNAL_API_KEY") or "").strip(),
        telegram_bot_token=(os.getenv("TELEGRAM_BOT_TOKEN") or "").strip(),
        telegram_webhook_url=(os.getenv("TELEGRAM_WEBHOOK_URL") or "").strip(),
        telegram_webhook_secret=(os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip(),
        report_timezone=(os.getenv("REPORT_TIMEZONE") or "Europe/Kyiv").strip(),
        sync_worker_cron=(os.getenv("SYNC_WORKER_CRON") or "0 18 * * *").strip(),
        cloud_backup_cron=(os.getenv("CLOUD_BACKUP_CRON") or "0 7 * * *").strip(),
        daily_reports_cron=(os.getenv("DAILY_REPORTS_CRON") or "45 21 * * *").strip(),
        heartbeat_interval_sec=int(os.getenv("HEARTBEAT_INTERVAL_SEC") or "600"),
        unblocker_lead_sec=int(os.getenv("UNBLOCKER_LEAD_SEC") or "1800"),
        health_port=int(os.getenv("HEALTH_PORT") or "9090"),
    )
