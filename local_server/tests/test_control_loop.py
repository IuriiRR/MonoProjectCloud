from local_server.config import Settings
from local_server.control_loop import cede_to_local, unblock_cloud


class FakeGateway:
    def __init__(self):
        self.calls = []

    def pause_job(self, name):
        self.calls.append(("pause", name))

    def resume_job(self, name):
        self.calls.append(("resume", name))

    def run_job_now(self, name):
        self.calls.append(("run_now", name))

    def push_job_forward(self, name, *, lead_seconds):
        self.calls.append(("push", name, lead_seconds))


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
        cloud_unblocker_job="unblocker",
        cloud_sync_worker_job="sync-worker",
        cloud_daily_reports_job="daily-reports",
        unblocker_lead_sec=1800,
    )


def test_cede_to_local_calls_expected_sequence(monkeypatch):
    gateway = FakeGateway()
    settings = _settings()
    monkeypatch.setattr("local_server.control_loop._delete_webhook", lambda _settings: None)

    cede_to_local(gateway, settings)

    assert ("pause", "sync-worker") in gateway.calls
    assert ("pause", "daily-reports") in gateway.calls
    assert ("resume", "unblocker") in gateway.calls
    assert ("push", "unblocker", 1800) in gateway.calls


def test_unblock_cloud_calls_expected_sequence(monkeypatch):
    gateway = FakeGateway()
    settings = _settings()
    monkeypatch.setattr("local_server.control_loop._set_webhook", lambda _settings: None)

    unblock_cloud(gateway, settings)

    assert ("resume", "sync-worker") in gateway.calls
    assert ("resume", "daily-reports") in gateway.calls
    assert ("run_now", "sync-worker") in gateway.calls
    assert ("run_now", "daily-reports") in gateway.calls
    assert ("pause", "unblocker") in gateway.calls
