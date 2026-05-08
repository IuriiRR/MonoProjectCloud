import json
import logging
import os
import threading
from typing import Any, Dict, List, Tuple

import functions_framework
import requests
from flask import Response, make_response
from loguru import logger

logging.basicConfig(level=logging.INFO)

# Try imports for different environments
try:
    from .models import SyncRequest, SyncResponse
except Exception:
    from models import SyncRequest, SyncResponse

MONO_API_URL = "https://api.monobank.ua"

# Simple currency mapping as a fallback since seed/currency.json is missing
CURRENCY_MAP = {
    980: {"code": 980, "name": "UAH", "symbol": "₴", "flag": "🇺🇦"},
    840: {"code": 840, "name": "USD", "symbol": "$", "flag": "🇺🇸"},
    978: {"code": 978, "name": "EUR", "symbol": "€", "flag": "🇪🇺"},
}

def _is_truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in ("1", "true", "yes", "on")


def _init_sentry() -> None:
    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if not dsn or _is_truthy(os.getenv("DISABLE_SENTRY")):
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.gcp import GcpIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[GcpIntegration()],
            send_default_pii=True,
            enable_logs=True,
            traces_sample_rate=1.0,
            profile_session_sample_rate=1.0,
            profile_lifecycle="trace",
        )
    except Exception:
        return


_init_sentry()


def _internal_auth_ok(headers) -> bool:
    # In prod, this should always be configured and required.
    internal_api_key = os.getenv("INTERNAL_API_KEY", "")
    if not internal_api_key:
        # Local/dev escape hatch (do NOT use in prod)
        return _is_truthy(os.getenv("AUTH_DISABLED")) or os.getenv("AUTH_MODE", "enabled").lower() == "disabled"
    presented = headers.get("X-Internal-Api-Key") or headers.get("X-Internal-API-Key")
    return presented == internal_api_key


def _require_internal(request) -> Response | None:
    if _internal_auth_ok(getattr(request, "headers", {}) or {}):
        return None
    return _error("Forbidden", 403, {"code": "FORBIDDEN"})


def get_currency_data(code: int) -> Dict[str, Any]:
    return CURRENCY_MAP.get(code, {"code": code, "name": "Unknown", "symbol": "", "flag": ""})

def _json_response(payload: Any, status: int = 200) -> Response:
    resp = make_response(json.dumps(payload, ensure_ascii=False), status)
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

def _error(message: str, status: int = 400, extra: Dict[str, Any] | None = None) -> Response:
    body: Dict[str, Any] = {"error": message}
    if extra:
        body.update(extra)
    return _json_response(body, status=status)


def _users_api_url() -> str:
    return os.getenv("USERS_API_URL", "http://users_api:8081")


def _accounts_api_url() -> str:
    return os.getenv("ACCOUNTS_API_URL", "http://accounts_api:8082")


def _sync_transactions_url() -> str:
    return os.getenv("SYNC_TRANSACTIONS_URL", "http://sync_transactions:8085")


def _trigger_tx_sync(user_id: str, token: str, accounts: List[Dict[str, Any]]):
    logger.info(f"Triggering transaction sync for user {user_id}")
    try:
        internal_headers: Dict[str, str] = {}
        internal_api_key = os.getenv("INTERNAL_API_KEY", "")
        if internal_api_key:
            internal_headers["X-Internal-Api-Key"] = internal_api_key
        tx_sync_resp = requests.post(
            f"{_sync_transactions_url()}/sync/transactions",
            json={"user_id": user_id, "mono_token": token, "accounts": accounts},
            headers=internal_headers,
            timeout=300 # Wait up to 5 mins in the background thread
        )
        if not tx_sync_resp.ok:
            logger.warning(f"Failed to trigger transaction sync for user {user_id}: {tx_sync_resp.text}")
        else:
            logger.info(f"Transaction sync finished for user {user_id}")
    except Exception as tx_e:
        logger.error(f"Error during background transaction sync for user {user_id}: {str(tx_e)}")


def run_sync_accounts() -> Dict[str, Any]:
    # 1. Fetch all users from users_api
    logger.info(f"Fetching users from {_users_api_url()}/users")
    internal_headers: Dict[str, str] = {}
    internal_api_key = os.getenv("INTERNAL_API_KEY", "")
    if internal_api_key:
        internal_headers["X-Internal-Api-Key"] = internal_api_key
    users_resp = requests.get(f"{_users_api_url()}/users", headers=internal_headers)
    if not users_resp.ok:
        raise ValueError(f"Failed to fetch users: {users_resp.text}")

    users = users_resp.json().get("users", [])
    active_users = [u for u in users if u.get("active") and u.get("mono_token")]

    processed_users = 0
    total_accounts_synced = 0
    errors = []

    for user in active_users:
        user_id = user["user_id"]
        token = user["mono_token"]

        logger.info(f"Syncing accounts for user {user_id}")

        # 2. Fetch accounts from Monobank API
        mono_headers = {"X-Token": token}
        mono_resp = requests.get(f"{MONO_API_URL}/personal/client-info", headers=mono_headers)

        if not mono_resp.ok:
            err_msg = f"Failed to fetch Monobank data for user {user_id}: {mono_resp.text}"
            logger.error(err_msg)
            errors.append(err_msg)
            continue

        mono_data = mono_resp.json()
        accounts_to_sync = []

        # Process regular accounts (cards)
        for acc in mono_data.get("accounts", []):
            accounts_to_sync.append({
                "id": acc["id"],
                "type": "card",
                "send_id": acc.get("sendId"),
                "currency": get_currency_data(acc["currencyCode"]),
                "balance": acc["balance"],
                "is_active": True, # Mono cards in client-info are active
            })

        # Process jars
        for jar in mono_data.get("jars", []):
            accounts_to_sync.append({
                "id": jar["id"],
                "type": "jar",
                "send_id": jar.get("sendId"),
                "currency": get_currency_data(jar["currencyCode"]),
                "balance": jar["balance"],
                "goal": jar.get("goal"),
                "title": jar.get("title"),
                "is_active": True,
            })

        if not accounts_to_sync:
            continue

        # 3. Put accounts to accounts_api with batch request
        logger.info(f"Sending {len(accounts_to_sync)} accounts to {_accounts_api_url()}")
        put_resp = requests.put(
            f"{_accounts_api_url()}/users/{user_id}/accounts",
            json={"accounts": accounts_to_sync},
            headers=internal_headers,
        )

        if not put_resp.ok:
            err_msg = f"Failed to update accounts for user {user_id}: {put_resp.text}"
            logger.error(err_msg)
            errors.append(err_msg)
            continue

        processed_users += 1
        total_accounts_synced += len(accounts_to_sync)

        # 4. Trigger transaction sync for this user (async), passing accounts we already have
        threading.Thread(target=_trigger_tx_sync, args=(user_id, token, accounts_to_sync)).start()

    return {
        "status": "success",
        "processed_users": processed_users,
        "total_accounts_synced": total_accounts_synced,
        "errors": errors,
    }

@functions_framework.http
def sync_worker(request):
    """
    Cloud Function HTTP entry point for syncing Monobank data.
    
    Paths:
      - POST /sync/accounts
    """
    if request.method == "OPTIONS":
        return _json_response({}, status=204)

    path = request.path or "/"
    parts = [p for p in path.split("/") if p]

    if not parts or parts[0] != "sync":
        return _error("Not found", 404)

    if len(parts) < 2 or parts[1] != "accounts":
        return _error("Not found", 404)

    if request.method != "POST":
        return _error("Method not allowed", 405)

    auth_err = _require_internal(request)
    if auth_err:
        return auth_err

    try:
        return _json_response(run_sync_accounts())
    except ValueError as e:
        return _error(str(e), status=500)
    except Exception as e:
        logger.exception("Unexpected error during sync")
        return _error(f"Internal server error: {str(e)}", status=500)

