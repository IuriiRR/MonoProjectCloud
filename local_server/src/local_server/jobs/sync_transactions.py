import os
from contextlib import contextmanager
from typing import Any, Dict

from functions.sync_transactions.main import SyncTransactionsRequest, run_sync_transactions
from local_server.config import Settings


@contextmanager
def _temporary_env(overrides: dict[str, str]):
    previous = {k: os.environ.get(k) for k in overrides}
    try:
        os.environ.update(overrides)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_for_user(settings: Settings, payload: Dict[str, Any]) -> dict:
    with _temporary_env(
        {
            "ACCOUNTS_API_URL": settings.accounts_api_url,
            "TRANSACTIONS_API_URL": settings.transactions_api_url,
            "INTERNAL_API_KEY": settings.internal_api_key,
        }
    ):
        req = SyncTransactionsRequest.model_validate(payload)
        return run_sync_transactions(req)
