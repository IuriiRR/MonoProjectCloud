import json

from flask import request as flask_request

from functions.accounts_api.main import accounts_api
from functions.users_api.main import users_api


def _json(resp):
    return json.loads(resp.get_data(as_text=True) or "{}")


def _create_user(app, user_id: str = "u1"):
    with app.test_request_context("/users", method="POST", json={"user_id": user_id}):
        resp = users_api(flask_request)
    assert resp.status_code == 201


def test_list_accounts_empty(app):
    _create_user(app, "u1")
    with app.test_request_context("/users/u1/accounts", method="GET"):
        resp = accounts_api(flask_request)
    assert resp.status_code == 200
    assert _json(resp) == {"accounts": []}


def test_accounts_requires_user(app):
    with app.test_request_context("/users/missing/accounts", method="GET"):
        resp = accounts_api(flask_request)
    assert resp.status_code == 404
    assert _json(resp)["error"] == "User not found"


def test_create_get_account(app):
    _create_user(app, "u1")
    payload = {
        "id": "a1",
        "type": "jar",
        "send_id": None,
        "currency": {"code": 980, "name": "UAH", "symbol": "₴", "flag": "🇺🇦"},
        "balance": 123,
        "is_active": True,
        "title": "Jar 1",
        "goal": None,
        "is_budget": False,
        "invested": 0,
    }
    with app.test_request_context("/users/u1/accounts", method="POST", json=payload):
        resp = accounts_api(flask_request)
    body = _json(resp)
    assert resp.status_code == 201
    assert body["account"]["id"] == "a1"
    assert body["account"]["type"] == "jar"
    assert body["account"]["currency"]["code"] == 980

    with app.test_request_context("/users/u1/accounts/a1", method="GET"):
        resp2 = accounts_api(flask_request)
    body2 = _json(resp2)
    assert resp2.status_code == 200
    assert body2["account"]["id"] == "a1"
    assert body2["account"]["title"] == "Jar 1"


def test_create_account_conflict(app):
    _create_user(app, "u1")
    with app.test_request_context(
        "/users/u1/accounts",
        method="POST",
        json={
            "id": "a1",
            "type": "jar",
            "currency": {"code": 980},
            "balance": 0,
        },
    ):
        accounts_api(flask_request)
    with app.test_request_context(
        "/users/u1/accounts",
        method="POST",
        json={
            "id": "a1",
            "type": "jar",
            "currency": {"code": 980},
            "balance": 0,
        },
    ):
        resp = accounts_api(flask_request)
    assert resp.status_code == 409


def test_patch_can_clear_nullable_fields(app):
    _create_user(app, "u1")
    with app.test_request_context(
        "/users/u1/accounts",
        method="POST",
        json={"id": "a1", "type": "jar", "currency": {"code": 980}, "balance": 0},
    ):
        resp = accounts_api(flask_request)
    assert resp.status_code == 201

    with app.test_request_context(
        "/users/u1/accounts/a1", method="PATCH", json={"title": "X", "send_id": "s1"}
    ):
        resp2 = accounts_api(flask_request)
    assert resp2.status_code == 200

    with app.test_request_context(
        "/users/u1/accounts/a1", method="PATCH", json={"title": None, "send_id": None}
    ):
        resp3 = accounts_api(flask_request)
    body3 = _json(resp3)
    assert resp3.status_code == 200
    assert body3["account"]["title"] is None
    assert body3["account"]["send_id"] is None


def test_patch_requires_fields(app):
    _create_user(app, "u1")
    with app.test_request_context(
        "/users/u1/accounts",
        method="POST",
        json={"id": "a1", "type": "jar", "currency": {"code": 980}, "balance": 0},
    ):
        accounts_api(flask_request)

    with app.test_request_context("/users/u1/accounts/a1", method="PATCH", json={}):
        resp = accounts_api(flask_request)
    assert resp.status_code == 400
    assert _json(resp)["error"] == "No updatable fields provided"


def test_patch_can_toggle_is_budget(app):
    _create_user(app, "u1")
    with app.test_request_context(
        "/users/u1/accounts",
        method="POST",
        json={
            "id": "a1",
            "type": "jar",
            "currency": {"code": 980},
            "balance": 0,
            "is_budget": False,
        },
    ):
        resp = accounts_api(flask_request)
    assert resp.status_code == 201

    with app.test_request_context(
        "/users/u1/accounts/a1", method="PATCH", json={"is_budget": True}
    ):
        resp2 = accounts_api(flask_request)
    assert resp2.status_code == 200
    assert _json(resp2)["account"]["is_budget"] is True

    with app.test_request_context(
        "/users/u1/accounts/a1", method="PATCH", json={"is_budget": False}
    ):
        resp3 = accounts_api(flask_request)
    assert resp3.status_code == 200
    assert _json(resp3)["account"]["is_budget"] is False


def test_delete_account(app):
    _create_user(app, "u1")
    with app.test_request_context(
        "/users/u1/accounts",
        method="POST",
        json={"id": "a1", "type": "jar", "currency": {"code": 980}, "balance": 0},
    ):
        accounts_api(flask_request)

    with app.test_request_context("/users/u1/accounts/a1", method="DELETE"):
        resp = accounts_api(flask_request)
    assert resp.status_code == 200
    assert _json(resp) == {"deleted": True, "account_id": "a1"}

    with app.test_request_context("/users/u1/accounts/a1", method="GET"):
        resp2 = accounts_api(flask_request)
    assert resp2.status_code == 404


def test_options(app):
    _create_user(app, "u1")
    with app.test_request_context("/users/u1/accounts", method="OPTIONS"):
        resp = accounts_api(flask_request)
    assert resp.status_code == 204


def test_batch_put_accounts(app):
    _create_user(app, "u1")
    
    # 1. First batch PUT
    payload = {
        "accounts": [
            {
                "id": "a1",
                "type": "jar",
                "currency": {"code": 980},
                "balance": 100,
                "title": "Batch Jar 1"
            },
            {
                "id": "a2",
                "type": "card",
                "currency": {"code": 840},
                "balance": 50,
            }
        ]
    }
    with app.test_request_context("/users/u1/accounts", method="PUT", json=payload):
        resp = accounts_api(flask_request)
    body = _json(resp)
    assert resp.status_code == 200
    assert body["processed"] == 2
    assert "a1" in body["ids"]
    assert "a2" in body["ids"]

    # 2. Verify creation
    with app.test_request_context("/users/u1/accounts/a1", method="GET"):
        resp_a1 = accounts_api(flask_request)
    assert _json(resp_a1)["account"]["title"] == "Batch Jar 1"

    # 3. Second batch PUT with overlap (duplicate skipping tolerance)
    payload_overlap = {
        "accounts": [
            {
                "id": "a1",
                "type": "jar",
                "currency": {"code": 980},
                "balance": 200, # Updated balance
                "title": "Batch Jar 1 Updated"
            },
            {
                "id": "a3", # New account
                "type": "card",
                "currency": {"code": 980},
                "balance": 0,
            }
        ]
    }
    with app.test_request_context("/users/u1/accounts", method="PUT", json=payload_overlap):
        resp_overlap = accounts_api(flask_request)
    body_overlap = _json(resp_overlap)
    assert resp_overlap.status_code == 200
    assert body_overlap["processed"] == 2
    assert "a1" in body_overlap["ids"]
    assert "a3" in body_overlap["ids"]

    # 4. Verify update and new creation
    with app.test_request_context("/users/u1/accounts/a1", method="GET"):
        resp_v1 = accounts_api(flask_request)
    assert _json(resp_v1)["account"]["balance"] == 200
    assert _json(resp_v1)["account"]["title"] == "Batch Jar 1 Updated"

    with app.test_request_context("/users/u1/accounts/a3", method="GET"):
        resp_v3 = accounts_api(flask_request)
    assert resp_v3.status_code == 200
    assert _json(resp_v3)["account"]["id"] == "a3"


def test_auth_user_not_found_returns_403(app, monkeypatch):
    import functions.accounts_api.main as accounts_main

    monkeypatch.setattr(accounts_main, "authenticate_request", lambda _req: ("missing", None, None))

    with app.test_request_context("/users/missing/accounts", method="GET"):
        resp = accounts_api(flask_request)
    assert resp.status_code == 403
    assert _json(resp)["code"] == "USER_NOT_FOUND"


def test_auth_forbidden_when_uid_mismatch(app, monkeypatch):
    import functions.accounts_api.main as accounts_main

    monkeypatch.setattr(accounts_main, "authenticate_request", lambda _req: ("u1", None, None))

    with app.test_request_context("/users/u2/accounts", method="GET"):
        resp = accounts_api(flask_request)
    assert resp.status_code == 403
    assert _json(resp)["code"] == "FORBIDDEN"


