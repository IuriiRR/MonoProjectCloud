from local_server.config import Settings
from local_server.jobs import daily_reports, sync_accounts
from unittest.mock import MagicMock


def _settings() -> Settings:
    return Settings(
        gcp_project_id="p1",
        users_api_url="https://users",
        accounts_api_url="https://accounts",
        transactions_api_url="https://tx",
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


def test_sync_accounts_job_calls_function_directly(monkeypatch):
    mock_result = {
        "status": "success",
        "processed_users": 1,
        "total_accounts_synced": 2,
        "errors": [],
    }
    monkeypatch.setattr("local_server.jobs.sync_accounts.run_sync_accounts", lambda: mock_result)

    result = sync_accounts.run(_settings())
    assert result["status"] == "success"
    assert result["processed_users"] == 1
