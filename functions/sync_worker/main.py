import json
import os
import threading
from typing import Any, Dict, List, Tuple

import functions_framework
import requests
from flask import Response, make_response
from loguru import logger

# Try imports for different environments
try:
    from .models import SyncRequest, SyncResponse
except Exception:
    from models import SyncRequest, SyncResponse

USERS_API_URL = os.environ.get("USERS_API_URL", "http://users_api:8081")
ACCOUNTS_API_URL = os.environ.get("ACCOUNTS_API_URL", "http://accounts_api:8082")
SYNC_TRANSACTIONS_URL = os.environ.get("SYNC_TRANSACTIONS_URL", "http://sync_transactions:8085")
MONO_API_URL = "https://api.monobank.ua"

# Simple currency mapping as a fallback since seed/currency.json is missing
CURRENCY_MAP = {
    980: {"code": 980, "name": "UAH", "symbol": "₴", "flag": "🇺🇦"},
    840: {"code": 840, "name": "USD", "symbol": "$", "flag": "🇺🇸"},
    978: {"code": 978, "name": "EUR", "symbol": "€", "flag": "🇪🇺"},
}

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

def _trigger_tx_sync(user_id: str, token: str):
    logger.info(f"Triggering transaction sync for user {user_id}")
    try:
        tx_sync_resp = requests.post(
            f"{SYNC_TRANSACTIONS_URL}/sync/transactions",
            json={"user_id": user_id, "mono_token": token},
            timeout=300 # Wait up to 5 mins in the background thread
        )
        if not tx_sync_resp.ok:
            logger.warning(f"Failed to trigger transaction sync for user {user_id}: {tx_sync_resp.text}")
        else:
            logger.info(f"Transaction sync finished for user {user_id}")
    except Exception as tx_e:
        logger.error(f"Error during background transaction sync for user {user_id}: {str(tx_e)}")

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

    try:
        # 1. Fetch all users from users_api
        logger.info(f"Fetching users from {USERS_API_URL}/users")
        users_resp = requests.get(f"{USERS_API_URL}/users")
        if not users_resp.ok:
            return _error(f"Failed to fetch users: {users_resp.text}", status=500)
        
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
            headers = {"X-Token": token}
            mono_resp = requests.get(f"{MONO_API_URL}/personal/client-info", headers=headers)
            
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
                    # Card specific fields mapping if any (maskedPan etc)
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
            logger.info(f"Sending {len(accounts_to_sync)} accounts to {ACCOUNTS_API_URL}")
            put_resp = requests.put(
                f"{ACCOUNTS_API_URL}/users/{user_id}/accounts",
                json={"accounts": accounts_to_sync}
            )
            
            if not put_resp.ok:
                err_msg = f"Failed to update accounts for user {user_id}: {put_resp.text}"
                logger.error(err_msg)
                errors.append(err_msg)
                continue
            
            processed_users += 1
            total_accounts_synced += len(accounts_to_sync)

            # 4. Trigger transaction sync for this user (async)
            threading.Thread(target=_trigger_tx_sync, args=(user_id, token)).start()

        return _json_response({
            "status": "success",
            "processed_users": processed_users,
            "total_accounts_synced": total_accounts_synced,
            "errors": errors
        })

    except Exception as e:
        logger.exception("Unexpected error during sync")
        return _error(f"Internal server error: {str(e)}", status=500)

