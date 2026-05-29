import os
from contextlib import contextmanager
from typing import Any, Dict

from functions.sync_worker.main import run_sync_accounts
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


def run(settings: Settings) -> Dict[str, Any]:
    with _temporary_env(
        {
            "USERS_API_URL": settings.users_api_url,
            "ACCOUNTS_API_URL": settings.accounts_api_url,
            "SYNC_TRANSACTIONS_URL": settings.sync_transactions_url,
            "INTERNAL_API_KEY": settings.internal_api_key,
        }
    ):
        return run_sync_accounts()
