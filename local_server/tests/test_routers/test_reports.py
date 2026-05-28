from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session

from local_server.models import Account, Transaction, User


def _ts(year: int, month: int, day: int) -> int:
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp())


def _seed_user(session: Session, user_id: str = "u1") -> User:
    user = User(user_id=user_id, mono_token="tok")
    session.add(user)
    session.commit()
    return user


def _seed_jar(session: Session, jar_id: str, user_id: str, balance: int = 0, is_budget: bool = True, title: str | None = None) -> Account:
    jar = Account(id=jar_id, user_id=user_id, type="jar", balance=balance, is_budget=is_budget, title=title)
    session.add(jar)
    session.commit()
    return jar


def _seed_tx(session: Session, tx_id: str, account_id: str, user_id: str, time: int, amount: int, balance: int) -> Transaction:
    tx = Transaction(id=tx_id, account_id=account_id, user_id=user_id, time=time, amount=amount, balance=balance)
    session.add(tx)
    session.commit()
    return tx


def test_monthly_no_budget_jars(client: TestClient, session: Session):
    _seed_user(session)
    _seed_jar(session, "jar1", "u1", balance=1000, is_budget=False)
    response = client.get("/reports/monthly?month=2026-05&user_id=u1")
    assert response.status_code == 200
    assert response.json() == {"month": "2026-05", "jars": []}


def test_monthly_with_budget_jar(client: TestClient, session: Session):
    _seed_user(session)
    _seed_jar(session, "jar1", "u1", balance=120000, is_budget=True, title="Groceries")

    # budget deposit on May 2
    _seed_tx(session, "tx1", "jar1", "u1", time=_ts(2026, 5, 2), amount=500000, balance=500000)
    # small cashback on May 5
    _seed_tx(session, "tx2", "jar1", "u1", time=_ts(2026, 5, 5), amount=2000, balance=502000)
    # withdrawal on May 10
    _seed_tx(session, "tx3", "jar1", "u1", time=_ts(2026, 5, 10), amount=-380000, balance=122000)
    # another withdrawal on May 20
    _seed_tx(session, "tx4", "jar1", "u1", time=_ts(2026, 5, 20), amount=-2000, balance=120000)

    response = client.get("/reports/monthly?month=2026-05&user_id=u1")
    assert response.status_code == 200
    body = response.json()
    assert body["month"] == "2026-05"
    assert len(body["jars"]) == 1

    jar = body["jars"][0]
    assert jar["id"] == "jar1"
    assert jar["title"] == "Groceries"
    assert jar["current_balance"] == 120000
    # start_balance = first_tx.balance - first_tx.amount = 500000 - 500000 = 0
    assert jar["start_balance"] == 0
    # budget = max positive = 500000
    assert jar["budget"] == 500000
    # total_deposits = 500000 + 2000 = 502000
    assert jar["total_deposits"] == 502000
    # spent = sum_all - budget = (500000 + 2000 - 380000 - 2000) - 500000 = 120000 - 500000 = -380000
    assert jar["spent"] == -380000


def test_monthly_no_transactions(client: TestClient, session: Session):
    _seed_user(session)
    _seed_jar(session, "jar1", "u1", balance=50000, is_budget=True, title="Savings")

    response = client.get("/reports/monthly?month=2026-05&user_id=u1")
    assert response.status_code == 200
    jar = response.json()["jars"][0]
    assert jar["start_balance"] == 50000  # falls back to current_balance
    assert jar["current_balance"] == 50000
    assert jar["budget"] == 0
    assert jar["total_deposits"] == 0
    assert jar["spent"] == 0


def test_monthly_invalid_month(client: TestClient, session: Session):
    response = client.get("/reports/monthly?month=2026-13")
    assert response.status_code == 422


def test_monthly_user_filter(client: TestClient, session: Session):
    _seed_user(session, "u1")
    _seed_user(session, "u2")
    _seed_jar(session, "jar1", "u1", balance=1000, is_budget=True, title="U1 jar")
    _seed_jar(session, "jar2", "u2", balance=2000, is_budget=True, title="U2 jar")

    response = client.get("/reports/monthly?month=2026-05&user_id=u1")
    assert response.status_code == 200
    jars = response.json()["jars"]
    assert len(jars) == 1
    assert jars[0]["id"] == "jar1"
