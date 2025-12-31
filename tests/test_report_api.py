import json

from flask import request as flask_request

from functions.accounts_api.main import accounts_api
from functions.report_api.main import report_api
from functions.transactions_api.main import transactions_api
from functions.users_api.main import users_api


def _json(resp):
    return json.loads(resp.get_data(as_text=True) or "{}")


def _create_user_and_accounts(app, user_id: str = "u1"):
    with app.test_request_context("/users", method="POST", json={"user_id": user_id}):
        users_api(flask_request)

    # Card + Jar
    with app.test_request_context(
        f"/users/{user_id}/accounts",
        method="POST",
        json={"id": "card1", "type": "card", "currency": {"code": 980}, "balance": 0},
    ):
        accounts_api(flask_request)

    with app.test_request_context(
        f"/users/{user_id}/accounts",
        method="POST",
        json={"id": "jar1", "type": "jar", "currency": {"code": 980}, "balance": 0, "title": "Budget Jar"},
    ):
        accounts_api(flask_request)


def test_daily_report_marks_covered_and_uncovered(app):
    _create_user_and_accounts(app, "u1")

    # Day: 2024-01-01 UTC
    # 00:00:10 earn +10000
    # 00:10:00 spend -3000 (covered)
    # 00:20:00 spend -8000 (partially uncovered by remaining 7000)
    with app.test_request_context(
        "/users/u1/accounts/card1/transactions",
        method="POST",
        json={"id": "e1", "time": 1704067210, "amount": 10000, "balance": 10000, "currency": {"code": 980}, "description": "Salary"},
    ):
        transactions_api(flask_request)

    with app.test_request_context(
        "/users/u1/accounts/card1/transactions",
        method="POST",
        json={"id": "s1", "time": 1704067800, "amount": -3000, "balance": 7000, "currency": {"code": 980}, "description": "Coffee"},
    ):
        transactions_api(flask_request)

    with app.test_request_context(
        "/users/u1/accounts/jar1/transactions",
        method="POST",
        json={"id": "s2", "time": 1704068400, "amount": -8000, "balance": -1000, "currency": {"code": 980}, "description": "Groceries"},
    ):
        transactions_api(flask_request)

    with app.test_request_context(
        "/users/u1/reports/daily",
        method="GET",
        query_string={"date": "2024-01-01", "tz": "Etc/UTC", "llm": "0"},
    ):
        resp = report_api(flask_request)

    assert resp.status_code == 200
    body = _json(resp)
    assert body["user_id"] == "u1"
    assert body["date"] == "2024-01-01"
    assert body["totals"]["earn_total"] == 10000
    assert body["totals"]["spend_total"] == 11000

    spends = {s["tx_id"]: s for s in body["spends"]}
    assert spends["s1"]["covered"] is True
    assert spends["s1"]["uncovered_cents"] == 0

    assert spends["s2"]["covered"] is False
    assert spends["s2"]["uncovered_cents"] == 1000

    md = body["report_markdown"]
    assert "✅" in md
    assert "❌" in md
    assert "💰" in md


def test_daily_report_requires_user_exists(app, monkeypatch):
    import functions.report_api.main as report_main

    monkeypatch.setattr(report_main, "authenticate_request", lambda _req: ("u1", None, None))

    with app.test_request_context(
        "/users/u1/reports/daily", method="GET", query_string={"date": "2024-01-01", "tz": "Etc/UTC", "llm": "0"}
    ):
        resp = report_api(flask_request)

    assert resp.status_code == 403
    assert _json(resp)["code"] == "USER_NOT_FOUND"

