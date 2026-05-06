from datetime import datetime, timezone

from local_server.cloud_scheduler import SchedulerGateway
from local_server.config import Settings


class FakeClient:
    def __init__(self):
        self.calls = []
        self.job = type("Job", (), {"schedule_time": None})()

    def pause_job(self, name):
        self.calls.append(("pause", name))

    def resume_job(self, name):
        self.calls.append(("resume", name))

    def run_job(self, name):
        self.calls.append(("run", name))

    def get_job(self, name):
        self.calls.append(("get", name))
        return self.job

    def update_job(self, job):
        self.calls.append(("update", job.schedule_time))


def _settings() -> Settings:
    return Settings(
        gcp_project_id="p1",
        users_api_url="https://users",
        accounts_api_url="https://accounts",
        transactions_api_url="https://tx",
        sync_transactions_url="https://sync-tx",
        internal_api_key="k",
        telegram_bot_token="t",
        telegram_webhook_url="https://webhook",
    )


def test_scheduler_gateway_job_operations():
    s = _settings()
    fake = FakeClient()
    gateway = SchedulerGateway(s, client=fake)

    gateway.pause_job("a")
    gateway.resume_job("b")
    gateway.run_job_now("c")
    gateway.push_job_forward("d", lead_seconds=123)

    assert fake.calls[0][0] == "pause"
    assert fake.calls[1][0] == "resume"
    assert fake.calls[2][0] == "run"
    assert fake.calls[3][0] == "get"
    assert fake.calls[4][0] == "update"
    assert isinstance(fake.calls[4][1], datetime)
    assert fake.calls[4][1].tzinfo == timezone.utc
