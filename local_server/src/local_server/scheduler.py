import logging
import threading

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from local_server.cloud_scheduler import SchedulerGateway
from local_server.config import load_settings
from local_server.control_loop import start_control_loop
from local_server.health import create_app
from local_server.jobs import daily_reports, sync_accounts


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _run_health_server(port: int) -> None:
    app = create_app()
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def main() -> None:
    settings = load_settings()
    gateway = SchedulerGateway(settings)

    health_thread = threading.Thread(target=_run_health_server, args=(settings.health_port,), daemon=True)
    health_thread.start()

    control_thread = threading.Thread(target=start_control_loop, args=(gateway, settings), daemon=True)
    control_thread.start()

    scheduler = BlockingScheduler(timezone=settings.report_timezone)
    scheduler.add_job(
        lambda: sync_accounts.run(settings),
        CronTrigger.from_crontab(settings.sync_worker_cron, timezone=settings.report_timezone),
        id="sync_worker",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: daily_reports.run(settings),
        CronTrigger.from_crontab(settings.daily_reports_cron, timezone=settings.report_timezone),
        id="daily_reports",
        replace_existing=True,
    )

    logger.info("Local scheduler started")
    scheduler.start()


if __name__ == "__main__":
    main()
