import json

from flask import request as flask_request

from functions.accounts_api.main import accounts_api
from functions.transactions_api.main import transactions_api
from functions.users_api.main import users_api


def _json(resp):
    return json.loads(resp.get_data(as_text=True) or "{}")


def _create_user_and_account(app, user_id: str = "u1", account_id: str = "a1"):
    with app.test_request_context("/users", method="POST", json={"user_id": user_id}):
        users_api(flask_request)
    
    payload = {
        "id": account_id,
        "type": "jar",
        "currency": {"code": 980, "name": "UAH"},
        "balance": 0,
    }
    with app.test_request_context(f"/users/{user_id}/accounts", method="POST", json=payload):
        accounts_api(flask_request)


def test_list_transactions_empty(app):
    _create_user_and_account(app, "u1", "a1")
    with app.test_request_context("/users/u1/accounts/a1/transactions", method="GET"):
        resp = transactions_api(flask_request)
    assert resp.status_code == 200
    assert _json(resp) == {"transactions": []}


def test_create_get_transaction(app):
    _create_user_and_account(app, "u1", "a1")
    payload = {
        "id": "t1",
        "time": 1703241600,
        "description": "Coffee",
        "amount": -5000,
        "operation_amount": -5000,
        "balance": 95000,
        "currency": {"code": 980},
        "mcc_code": 5812,
    }
    with app.test_request_context("/users/u1/accounts/a1/transactions", method="POST", json=payload):
        resp = transactions_api(flask_request)
    assert resp.status_code == 201
    
    with app.test_request_context("/users/u1/accounts/a1/transactions/t1", method="GET"):
        resp2 = transactions_api(flask_request)
    body2 = _json(resp2)
    assert resp2.status_code == 200
    assert body2["transaction"]["id"] == "t1"
    assert body2["transaction"]["description"] == "Coffee"


def test_list_transactions_sorting_and_filtering(app):
    _create_user_and_account(app, "u1", "a1")
    # T1 (older)
    with app.test_request_context(
        "/users/u1/accounts/a1/transactions", 
        method="POST", 
        json={"id": "t1", "time": 100, "amount": -10, "balance": 90, "currency": {"code": 980}}
    ):
        transactions_api(flask_request)
    # T2 (newer)
    with app.test_request_context(
        "/users/u1/accounts/a1/transactions", 
        method="POST", 
        json={"id": "t2", "time": 200, "amount": -10, "balance": 80, "currency": {"code": 980}}
    ):
        transactions_api(flask_request)

    # Default: newest first
    with app.test_request_context("/users/u1/accounts/a1/transactions", method="GET"):
        resp = transactions_api(flask_request)
    txs = _json(resp)["transactions"]
    assert len(txs) == 2
    assert txs[0]["id"] == "t2"
    assert txs[1]["id"] == "t1"

    # Filter by since
    with app.test_request_context("/users/u1/accounts/a1/transactions", method="GET", query_string={"since": "150"}):
        resp = transactions_api(flask_request)
    txs = _json(resp)["transactions"]
    assert len(txs) == 1
    assert txs[0]["id"] == "t2"


def test_patch_transaction(app):
    _create_user_and_account(app, "u1", "a1")
    with app.test_request_context(
        "/users/u1/accounts/a1/transactions", 
        method="POST", 
        json={"id": "t1", "time": 100, "amount": -10, "balance": 90, "currency": {"code": 980}}
    ):
        transactions_api(flask_request)

    with app.test_request_context(
        "/users/u1/accounts/a1/transactions/t1", 
        method="PATCH", 
        json={"comment": "Nice coffee"}
    ):
        resp = transactions_api(flask_request)
    assert resp.status_code == 200
    assert _json(resp)["transaction"]["comment"] == "Nice coffee"


def test_delete_transaction(app):
    _create_user_and_account(app, "u1", "a1")
    with app.test_request_context(
        "/users/u1/accounts/a1/transactions", 
        method="POST", 
        json={"id": "t1", "time": 100, "amount": -10, "balance": 90, "currency": {"code": 980}}
    ):
        transactions_api(flask_request)

    with app.test_request_context("/users/u1/accounts/a1/transactions/t1", method="DELETE"):
        resp = transactions_api(flask_request)
    assert resp.status_code == 200
    
    with app.test_request_context("/users/u1/accounts/a1/transactions/t1", method="GET"):
        resp2 = transactions_api(flask_request)
    assert resp2.status_code == 404


def test_global_transactions_endpoint(app):
    # Setup: 2 users, each with 1 account and 1 transaction
    _create_user_and_account(app, "user1", "acc1")
    _create_user_and_account(app, "user2", "acc2")

    # Transaction for user1
    with app.test_request_context(
        "/users/user1/accounts/acc1/transactions",
        method="POST",
        json={"id": "t1", "time": 100, "amount": -10, "balance": 90, "currency": {"code": 980}},
    ):
        transactions_api(flask_request)

    # Transaction for user2
    with app.test_request_context(
        "/users/user2/accounts/acc2/transactions",
        method="POST",
        json={"id": "t2", "time": 200, "amount": -20, "balance": 80, "currency": {"code": 980}},
    ):
        transactions_api(flask_request)

    # Test GET /transactions
    with app.test_request_context("/transactions", method="GET"):
        resp = transactions_api(flask_request)
    
    assert resp.status_code == 200
    body = _json(resp)
    txs = body["transactions"]
    
    assert len(txs) == 2
    # Should be sorted by time DESC: t2 then t1
    assert txs[0]["id"] == "t2"
    assert txs[0]["user_id"] == "user2"
    assert txs[0]["account_id"] == "acc2"
    
    assert txs[1]["id"] == "t1"
    assert txs[1]["user_id"] == "user1"
    assert txs[1]["account_id"] == "acc1"

    # Test filtering
    with app.test_request_context("/transactions", method="GET", query_string={"since": "150"}):
        resp = transactions_api(flask_request)
    
    assert resp.status_code == 200
    txs = _json(resp)["transactions"]
    assert len(txs) == 1
    assert txs[0]["id"] == "t2"


