from local_server.health import create_app, mark_heartbeat


def test_healthz_returns_200():
    app = create_app()
    client = app.test_client()
    mark_heartbeat()

    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["last_heartbeat_at"] is not None
