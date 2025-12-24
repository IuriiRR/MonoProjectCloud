import pytest
from unittest.mock import patch, MagicMock
from functions.sync_worker.main import sync_worker

@pytest.fixture
def mock_requests():
    with patch("functions.sync_worker.main.requests") as mock:
        yield mock

def test_sync_accounts_success(app, mock_requests):
    # 1. Mock users_api/users response
    mock_users_resp = MagicMock()
    mock_users_resp.ok = True
    mock_users_resp.json.return_value = {
        "users": [
            {"user_id": "u1", "active": True, "mono_token": "token1"},
            {"user_id": "u2", "active": False, "mono_token": "token2"}, # Inactive, should be skipped
        ]
    }
    
    # 2. Mock Monobank API response
    mock_mono_resp = MagicMock()
    mock_mono_resp.ok = True
    mock_mono_resp.json.return_value = {
        "accounts": [
            {"id": "a1", "currencyCode": 980, "balance": 1000, "type": "black", "sendId": "s1"}
        ],
        "jars": [
            {"id": "j1", "currencyCode": 980, "balance": 5000, "goal": 10000, "title": "Jar 1", "sendId": "s2"}
        ]
    }
    
    # 3. Mock accounts_api PUT response
    mock_accounts_resp = MagicMock()
    mock_accounts_resp.ok = True
    mock_accounts_resp.json.return_value = {"processed": 2, "ids": ["a1", "j1"]}
    
    # Configure the mock to return different responses based on the URL
    def side_effect(method, url, **kwargs):
        if "users_api" in url:
            return mock_users_resp
        if "api.monobank.ua" in url:
            return mock_mono_resp
        if "accounts_api" in url:
            return mock_accounts_resp
        return MagicMock(ok=False)

    mock_requests.get.side_effect = lambda url, **kwargs: side_effect("GET", url, **kwargs)
    mock_requests.put.side_effect = lambda url, **kwargs: side_effect("PUT", url, **kwargs)

    # Call the function within app context
    with app.app_context():
        class MockRequest:
            method = "POST"
            path = "/sync/accounts"
            def get_json(self, silent=False):
                return {}

            @property
            def data(self):
                return b"{}"

        response = sync_worker(MockRequest())
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["processed_users"] == 1 # Only u1
    assert data["total_accounts_synced"] == 2 # a1 and j1

def test_sync_accounts_not_found(app, mock_requests):
    with app.app_context():
        class MockRequest:
            method = "POST"
            path = "/sync/invalid"
    
        response = sync_worker(MockRequest())
    assert response.status_code == 404

def test_sync_accounts_wrong_method(app, mock_requests):
    with app.app_context():
        class MockRequest:
            method = "GET"
            path = "/sync/accounts"
    
        response = sync_worker(MockRequest())
    assert response.status_code == 405

