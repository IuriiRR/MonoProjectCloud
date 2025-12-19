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
    Patch the users_api function to use an in-memory Firestore fake.

    This keeps tests fast and independent from the Firestore emulator.
    """
    import functions.users_api.main as main
    from tests.fakes import firestore as fake_firestore

    monkeypatch.setattr(main, "get_db", lambda: fake_db)
    monkeypatch.setattr(main.firestore, "SERVER_TIMESTAMP", fake_firestore.SERVER_TIMESTAMP)


