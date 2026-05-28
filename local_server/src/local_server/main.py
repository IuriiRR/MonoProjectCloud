import logging
import threading
from contextlib import asynccontextmanager
from threading import Event

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from local_server.admin import setup_admin
from local_server.database import create_db_and_tables, engine
from local_server.health import _state as health_state
from local_server.routers import accounts, reports, sync, transactions, users

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_stop_event: Event | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _stop_event

    create_db_and_tables()
    setup_admin(app, engine)

    _stop_event = Event()

    # Scheduler + control loop require GCP credentials; skip gracefully in dev/test
    try:
        from local_server.cloud_scheduler import SchedulerGateway
        from local_server.config import load_settings
        from local_server.control_loop import start_control_loop, unblock_cloud
        from local_server.jobs import daily_reports, sync_accounts, sync_accounts_cloud

        settings = load_settings()
        gateway = SchedulerGateway(settings)

        # scheduler.add_job(
        #     lambda: sync_accounts.run(settings),
        #     CronTrigger.from_crontab(settings.sync_worker_cron, timezone=settings.report_timezone),
        #     id="sync_worker",
        #     replace_existing=True,
        # )
        # scheduler.add_job(
        #     lambda: daily_reports.run(settings),
        #     CronTrigger.from_crontab(settings.daily_reports_cron, timezone=settings.report_timezone),
        #     id="daily_reports",
        #     replace_existing=True,
        # )
        # scheduler.add_job(
        #     lambda: sync_accounts_cloud.run(settings),
        #     CronTrigger.from_crontab(settings.cloud_backup_cron, timezone=settings.report_timezone),
        #     id="sync_worker_cloud",
        #     replace_existing=True,
        # )

        control_thread = threading.Thread(
            target=start_control_loop,
            args=(gateway, settings, _stop_event),
            daemon=True,
        )
        control_thread.start()

        scheduler.start()
        logger.info("Scheduler and control loop started")

        yield

        # Graceful shutdown: restore cloud jobs before stopping
        _stop_event.set()
        try:
            unblock_cloud(gateway, settings)
        except Exception as e:
            logger.error("unblock_cloud failed during shutdown: %s", e)
        scheduler.shutdown()

    except Exception as e:
        logger.warning("Scheduler/control loop skipped (likely missing GCP creds): %s", e)
        scheduler.start()
        yield
        scheduler.shutdown()


app = FastAPI(title="CloudApi Local Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(sync.router, prefix="/sync", tags=["sync"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])


@app.get("/")
async def root():
    return {"message": "CloudApi Local Server is running"}


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "last_heartbeat_at": health_state["last_heartbeat_at"],
        "last_error": health_state["last_error"],
    }
