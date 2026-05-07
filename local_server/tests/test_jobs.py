from unittest.mock import MagicMock

from local_server.config import Settings
from local_server.jobs import daily_reports, sync_accounts


def _settings() -> Settings:
    return Settings(
        gcp_project_id="p1",
        users_api_url="https://users",
        accounts_api_url="https://accounts",
        transactions_api_url="https://tx",
        sync_worker_url="http://127.0.0.1:8084",
        sync_transactions_url="https://sync-tx",
        internal_api_key="k",
        telegram_bot_token="t",
        telegram_webhook_url="https://webhook",
    )


def test_daily_reports_job_success(monkeypatch):
    response = MagicMock(ok=True)
    response.json.return_value = {"sent": 4}
    monkeypatch.setattr("local_server.jobs.daily_reports.requests.post", lambda *args, **kwargs: response)

    result = daily_reports.run(_settings())
    assert result["sent"] == 4


def test_sync_accounts_job_calls_local_sync_worker(monkeypatch):
    captured: dict = {}

    response = MagicMock(ok=True)
    response.json.return_value = {
        "status": "success",
        "processed_users": 1,
        "total_accounts_synced": 2,
        "errors": [],
    }

    def _fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return response

    monkeypatch.setattr("local_server.jobs.sync_accounts.requests.post", _fake_post)

    result = sync_accounts.run(_settings())
    assert result["status"] == "success"
    assert result["processed_users"] == 1
    assert captured["url"] == "http://127.0.0.1:8084/sync/accounts"
    assert captured["headers"] == {"X-Internal-Api-Key": "k"}
