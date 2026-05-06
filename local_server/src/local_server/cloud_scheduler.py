from datetime import datetime, timedelta, timezone
from .config import Settings

try:
    from google.cloud import scheduler_v1
except Exception:  # pragma: no cover
    scheduler_v1 = None  # type: ignore[assignment]


class SchedulerGateway:
    def __init__(self, settings: Settings, client=None) -> None:
        self.settings = settings
        if client is not None:
            self.client = client
        elif scheduler_v1 is not None:
            self.client = scheduler_v1.CloudSchedulerClient()
        else:
            raise RuntimeError("google-cloud-scheduler is not installed")

    def _path(self, job_name: str) -> str:
        return (
            f"projects/{self.settings.gcp_project_id}/"
            f"locations/{self.settings.gcp_scheduler_region}/jobs/{job_name}"
        )

    def pause_job(self, job_name: str) -> None:
        self.client.pause_job(name=self._path(job_name))

    def resume_job(self, job_name: str) -> None:
        self.client.resume_job(name=self._path(job_name))

    def run_job_now(self, job_name: str) -> None:
        self.client.run_job(name=self._path(job_name))

    def push_job_forward(self, job_name: str, *, lead_seconds: int) -> None:
        job = self.client.get_job(name=self._path(job_name))
        next_run = datetime.now(timezone.utc) + timedelta(seconds=max(lead_seconds, 1))
        job.schedule_time = next_run
        self.client.update_job(job=job)
