import json

from flask import request as flask_request

from functions.users_api.main import users_api


def _json(resp):
    return json.loads(resp.get_data(as_text=True) or "{}")


def test_list_users_empty(app):
    with app.test_request_context("/users", method="GET"):
        resp = users_api(flask_request)
    assert resp.status_code == 200
    assert _json(resp) == {"users": []}


def test_create_get_user_with_nullable_mono_token(app):
    with app.test_request_context(
        "/users",
        method="POST",
        json={"user_id": "u1", "username": "Alice", "mono_token": None, "active": True},
    ):
        resp = users_api(flask_request)
    body = _json(resp)
    assert resp.status_code == 201
    assert body["user"]["user_id"] == "u1"
    assert body["user"]["mono_token"] is None

    with app.test_request_context("/users/u1", method="GET"):
        resp2 = users_api(flask_request)
    body2 = _json(resp2)
    assert resp2.status_code == 200
    assert body2["user"]["user_id"] == "u1"
    assert body2["user"]["mono_token"] is None


def test_create_conflict(app):
    with app.test_request_context("/users", method="POST", json={"user_id": "u1"}):
        users_api(flask_request)
    with app.test_request_context("/users", method="POST", json={"user_id": "u1"}):
        resp = users_api(flask_request)
    assert resp.status_code == 409


def test_patch_can_clear_mono_token(app):
    with app.test_request_context(
        "/users",
        method="POST",
        json={"user_id": "u1", "mono_token": "secret", "active": True},
    ):
        resp = users_api(flask_request)
    assert resp.status_code == 201

    with app.test_request_context("/users/u1", method="PATCH", json={"mono_token": None}):
        resp2 = users_api(flask_request)
    body2 = _json(resp2)
    assert resp2.status_code == 200
    assert body2["user"]["mono_token"] is None


def test_patch_requires_fields(app):
    with app.test_request_context("/users", method="POST", json={"user_id": "u1"}):
        users_api(flask_request)

    with app.test_request_context("/users/u1", method="PATCH", json={}):
        resp = users_api(flask_request)
    assert resp.status_code == 400
    assert _json(resp)["error"] == "No updatable fields provided"


def test_delete_user(app):
    with app.test_request_context("/users", method="POST", json={"user_id": "u1"}):
        users_api(flask_request)

    with app.test_request_context("/users/u1", method="DELETE"):
        resp = users_api(flask_request)
    assert resp.status_code == 200
    assert _json(resp) == {"deleted": True, "user_id": "u1"}

    with app.test_request_context("/users/u1", method="GET"):
        resp2 = users_api(flask_request)
    assert resp2.status_code == 404


def test_options(app):
    with app.test_request_context("/users", method="OPTIONS"):
        resp = users_api(flask_request)
    assert resp.status_code == 204


def test_auth_missing_token_returns_401(app, monkeypatch):
    import functions.users_api.main as users_main

    monkeypatch.setattr(
        users_main,
        "authenticate_request",
        lambda _req: (None, {"error": "Missing Authorization header", "code": "UNAUTHENTICATED"}, 401),
    )

    with app.test_request_context("/users/u1", method="GET"):
        resp = users_api(flask_request)
    assert resp.status_code == 401
    assert _json(resp)["code"] == "UNAUTHENTICATED"


def test_auth_user_not_found_returns_403(app, monkeypatch):
    import functions.users_api.main as users_main

    monkeypatch.setattr(users_main, "authenticate_request", lambda _req: ("u_missing", None, None))

    with app.test_request_context("/users/u_missing", method="GET"):
        resp = users_api(flask_request)
    assert resp.status_code == 403
    body = _json(resp)
    assert body["code"] == "USER_NOT_FOUND"


def test_auth_forbidden_when_uid_mismatch(app, monkeypatch):
    import functions.users_api.main as users_main

    monkeypatch.setattr(users_main, "authenticate_request", lambda _req: ("u1", None, None))

    with app.test_request_context("/users/u2", method="GET"):
        resp = users_api(flask_request)
    assert resp.status_code == 403
    assert _json(resp)["code"] == "FORBIDDEN"


def test_family_invite_flow(app, monkeypatch):
    import functions.users_api.main as users_main
    
    # 1. Create User A and User B
    with app.test_request_context("/users", method="POST", json={"user_id": "uA"}):
        users_api(flask_request)
    with app.test_request_context("/users", method="POST", json={"user_id": "uB"}):
        users_api(flask_request)

    # 2. User A generates invite
    monkeypatch.setattr(users_main, "authenticate_request", lambda _req: ("uA", None, None))
    with app.test_request_context("/users/uA/family/invite", method="POST"):
        resp = users_api(flask_request)
    assert resp.status_code == 200
    code = _json(resp)["code"]

    # 3. User B joins using code
    monkeypatch.setattr(users_main, "authenticate_request", lambda _req: ("uB", None, None))
    with app.test_request_context("/users/uB/family/join", method="POST", json={"code": code}):
        resp = users_api(flask_request)
    assert resp.status_code == 200
    assert _json(resp)["status"] == "request_sent"

    # 4. User A checks requests
    monkeypatch.setattr(users_main, "authenticate_request", lambda _req: ("uA", None, None))
    with app.test_request_context("/users/uA/family/requests", method="GET"):
        resp = users_api(flask_request)
    assert resp.status_code == 200
    reqs = _json(resp)["requests"]
    assert len(reqs) == 1
    assert reqs[0]["requester_id"] == "uB"

    # 5. User A accepts
    with app.test_request_context(f"/users/uA/family/requests/uB", method="POST", json={"action": "accept"}):
        resp = users_api(flask_request)
    assert resp.status_code == 200

    # 6. Verify family_members in profile
    with app.test_request_context("/users/uA", method="GET"):
        resp = users_api(flask_request)
    assert "uB" in _json(resp)["user"]["family_members"]

    monkeypatch.setattr(users_main, "authenticate_request", lambda _req: ("uB", None, None))
    with app.test_request_context("/users/uB", method="GET"):
        resp = users_api(flask_request)
    assert "uA" in _json(resp)["user"]["family_members"]

    # 7. Remove member
    monkeypatch.setattr(users_main, "authenticate_request", lambda _req: ("uA", None, None))
    with app.test_request_context("/users/uA/family/members/uB", method="DELETE"):
        resp = users_api(flask_request)
    assert resp.status_code == 200

    with app.test_request_context("/users/uA", method="GET"):
        resp = users_api(flask_request)
    assert "uB" not in _json(resp)["user"]["family_members"]