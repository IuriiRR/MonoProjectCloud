import pytest
from unittest.mock import patch, MagicMock
from functions.sync_transactions.main import sync_transactions

@pytest.fixture
def mock_requests():
    with patch("functions.sync_transactions.main.requests") as mock:
        yield mock

def test_sync_transactions_success(app, mock_requests, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "test-internal-key")
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.delenv("AUTH_MODE", raising=False)
    # 1. Mock accounts_api response
    mock_acc_resp = MagicMock()
    mock_acc_resp.ok = True
    mock_acc_resp.json.return_value = {
        "accounts": [
            {"id": "a1", "currency": {"code": 980}}
        ]
    }
    
    # 2. Mock Monobank API response
    mock_mono_resp = MagicMock()
    mock_mono_resp.ok = True
    mock_mono_resp.status_code = 200
    mock_mono_resp.json.return_value = [
        {"id": "t1", "time": 1703241600, "amount": -5000, "balance": 95000, "mcc": 5812}
    ]
    
    # 3. Mock transactions_api PUT response
    mock_tx_resp = MagicMock()
    mock_tx_resp.ok = True
    mock_tx_resp.json.return_value = {"processed": 1, "ids": ["t1"]}
    
    def side_effect(method, url, **kwargs):
        if "accounts_api" in url:
            return mock_acc_resp
        if "api.monobank.ua" in url:
            return mock_mono_resp
        if "transactions_api" in url:
            return mock_tx_resp
        return MagicMock(ok=False)

    mock_requests.get.side_effect = lambda url, **kwargs: side_effect("GET", url, **kwargs)
    mock_requests.put.side_effect = lambda url, **kwargs: side_effect("PUT", url, **kwargs)

    with app.app_context():
        class MockRequest:
            method = "POST"
            headers = {"X-Internal-Api-Key": "test-internal-key"}
            def get_json(self, silent=True):
                return {"user_id": "u1", "mono_token": "token1"}

        response = sync_transactions(MockRequest())
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["processed_accounts"] == 1
    assert data["total_transactions_synced"] == 1

def test_sync_transactions_rate_limit(app, mock_requests, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "test-internal-key")
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.delenv("AUTH_MODE", raising=False)
    # Mock rate limit then success
    mock_acc_resp = MagicMock(ok=True)
    mock_acc_resp.json.return_value = {"accounts": [{"id": "a1"}]}
    
    mock_mono_429 = MagicMock(status_code=429, ok=False)
    mock_mono_200 = MagicMock(status_code=200, ok=True)
    mock_mono_200.json.return_value = []
    
    mock_requests.get.side_effect = [mock_acc_resp, mock_mono_429, mock_mono_200]
    
    with app.app_context():
        class MockRequest:
            method = "POST"
            headers = {"X-Internal-Api-Key": "test-internal-key"}
            def get_json(self, silent=True):
                return {"user_id": "u1", "mono_token": "token1"}

        # Patch time.sleep to avoid waiting during tests
        with patch("time.sleep"):
            response = sync_transactions(MockRequest())
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["processed_accounts"] == 1


def test_sync_transactions_requires_internal_key(app, mock_requests, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "test-internal-key")
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.delenv("AUTH_MODE", raising=False)
    with app.app_context():
        class MockRequest:
            method = "POST"
            headers = {}

            def get_json(self, silent=True):
                return {"user_id": "u1", "mono_token": "token1"}

        response = sync_transactions(MockRequest())

    assert response.status_code == 403

