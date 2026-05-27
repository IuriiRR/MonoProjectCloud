from fastapi.testclient import TestClient

def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "CloudApi Local Server is running"}

def test_healthz(client: TestClient):
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "last_heartbeat_at" in body
    assert "last_error" in body

def test_list_users(client: TestClient):
    response = client.get("/users/")
    assert response.status_code == 200
    assert response.json() == {"users": []}

def test_list_accounts(client: TestClient):
    response = client.get("/accounts/")
    assert response.status_code == 200
    assert response.json() == {"accounts": []}

def test_sync_accounts(client: TestClient):
    response = client.post("/sync/accounts")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
