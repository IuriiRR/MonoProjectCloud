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




