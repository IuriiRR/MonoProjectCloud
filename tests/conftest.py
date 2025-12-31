import pytest
from flask import Flask


@pytest.fixture()
def app() -> Flask:
    return Flask(__name__)


@pytest.fixture()
def fake_db():
    from tests.fakes.firestore import FakeFirestore

    return FakeFirestore()


@pytest.fixture(autouse=True)
def patch_users_api_db(monkeypatch, fake_db):
    """
    Patch cloud functions to use an in-memory Firestore fake.

    This keeps tests fast and independent from the Firestore emulator.
    """
    import functions.accounts_api.main as accounts_main
    import functions.transactions_api.main as transactions_main
    import functions.users_api.main as users_main
    import functions.report_api.main as report_main
    import functions.sync_worker.main as sync_worker_main
    import functions.sync_transactions.main as sync_transactions_main
    from tests.fakes import firestore as fake_firestore

    monkeypatch.setattr(users_main, "get_db", lambda: fake_db)
    monkeypatch.setattr(
        users_main.firestore, "SERVER_TIMESTAMP", fake_firestore.SERVER_TIMESTAMP
    )

    monkeypatch.setattr(accounts_main, "get_db", lambda: fake_db)
    monkeypatch.setattr(
        accounts_main.firestore, "SERVER_TIMESTAMP", fake_firestore.SERVER_TIMESTAMP
    )

    monkeypatch.setattr(transactions_main, "get_db", lambda: fake_db)
    monkeypatch.setattr(
        transactions_main.firestore, "SERVER_TIMESTAMP", fake_firestore.SERVER_TIMESTAMP
    )

    monkeypatch.setattr(report_main, "get_db", lambda: fake_db)
    monkeypatch.setattr(
        report_main.firestore, "SERVER_TIMESTAMP", fake_firestore.SERVER_TIMESTAMP
    )

    # Sync workers don't use get_db directly but it's good practice to have them ready

    # Default auth behavior for unit tests:
    # run everything as "internal" so existing CRUD tests don't need Firebase tokens.
    monkeypatch.setattr(
        users_main,
        "authenticate_request",
        lambda _req: (users_main.INTERNAL_UID, None, None),
    )
    monkeypatch.setattr(
        accounts_main,
        "authenticate_request",
        lambda _req: (accounts_main.INTERNAL_UID, None, None),
    )
    monkeypatch.setattr(
        transactions_main,
        "authenticate_request",
        lambda _req: (transactions_main.INTERNAL_UID, None, None),
    )

    monkeypatch.setattr(
        report_main,
        "authenticate_request",
        lambda _req: (report_main.INTERNAL_UID, None, None),
    )
