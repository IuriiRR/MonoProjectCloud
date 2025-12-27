import json
import os
import time
import requests
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
import functions_framework
from flask import Response, make_response
from loguru import logger
from pydantic import ValidationError

# Try imports for different environments
try:
    from .models import SyncTransactionsRequest, SyncTransactionsResponse
except Exception:
    from models import SyncTransactionsRequest, SyncTransactionsResponse

ACCOUNTS_API_URL = os.environ.get("ACCOUNTS_API_URL", "http://accounts_api:8082")
TRANSACTIONS_API_URL = os.environ.get("TRANSACTIONS_API_URL", "http://transactions_api:8083")
MONO_API_URL = "https://api.monobank.ua"

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

@functions_framework.http
def sync_transactions(request):
    """
    Cloud Function HTTP entry point for syncing transactions for a single user.
    
    Expects POST /sync/transactions with body:
    {
        "user_id": "...",
        "mono_token": "...",
        "days": 30
    }
    """
    if request.method == "OPTIONS":
        return _json_response({}, status=204)

    if request.method != "POST":
        return _error("Method not allowed", 405)

    try:
        body_json = request.get_json(silent=True) or {}
        try:
            req = SyncTransactionsRequest.model_validate(body_json)
        except ValidationError as e:
            return _error("Validation error", 400, {"details": e.errors()})

        user_id = req.user_id
        token = req.mono_token
        days = req.days

        # 1. Fetch accounts for this user
        logger.info(f"Fetching accounts for user {user_id} from {ACCOUNTS_API_URL}")
        acc_resp = requests.get(f"{ACCOUNTS_API_URL}/users/{user_id}/accounts")
        if not acc_resp.ok:
            return _error(f"Failed to fetch accounts: {acc_resp.text}", status=500)
        
        accounts = acc_resp.json().get("accounts", [])
        if not accounts:
            logger.info(f"No accounts found for user {user_id}")
            return _json_response({
                "status": "success",
                "user_id": user_id,
                "processed_accounts": 0,
                "total_transactions_synced": 0
            })

        # Calculate time range
        to_time = int(time.time())
        from_time = to_time - (days * 24 * 60 * 60)
        
        processed_accounts = 0
        total_transactions_synced = 0
        errors = []

        for acc in accounts:
            account_id = acc["id"]
            logger.info(f"Syncing transactions for account {account_id} (user {user_id})")
            
            # 2. Fetch transactions from Monobank API
            headers = {"X-Token": token}
            url = f"{MONO_API_URL}/personal/statement/{account_id}/{from_time}/{to_time}"
            
            success = False
            retries = 0
            while not success and retries < 2:
                mono_resp = requests.get(url, headers=headers)
                
                if mono_resp.status_code == 429:
                    logger.warning(f"Rate limited by Monobank. Waiting 60 seconds...")
                    time.sleep(60)
                    retries += 1
                    continue
                
                if not mono_resp.ok:
                    err_msg = f"Failed to fetch Monobank transactions for account {account_id}: {mono_resp.text}"
                    logger.error(err_msg)
                    errors.append(err_msg)
                    break
                
                success = True
                transactions_data = mono_resp.json()
                if not transactions_data:
                    logger.info(f"No transactions found for account {account_id}")
                    processed_accounts += 1
                    break

                # Map Monobank transactions to our internal format
                # Monobank uses CamelCase for some fields in statements, or at least different from client-info.
                # Actually, based on documentation: id, time, description, mcc, amount, balance, etc.
                mapped_txs = []
                for tx in transactions_data:
                    mapped_txs.append({
                        "id": tx["id"],
                        "time": tx["time"],
                        "description": tx.get("description", ""),
                        "amount": tx["amount"],
                        "operation_amount": tx.get("operationAmount"),
                        "balance": tx["balance"],
                        "currency": acc.get("currency"), # Use account's currency info
                        "mcc_code": tx.get("mcc"),
                        "comment": tx.get("comment"),
                        "hold": tx.get("hold", False)
                    })

                # 3. Put transactions to transactions_api with batch request
                logger.info(f"Sending {len(mapped_txs)} transactions to {TRANSACTIONS_API_URL}")
                tx_put_url = f"{TRANSACTIONS_API_URL}/users/{user_id}/accounts/{account_id}/transactions"
                put_resp = requests.put(tx_put_url, json={"transactions": mapped_txs})
                
                if not put_resp.ok:
                    err_msg = f"Failed to update transactions for account {account_id}: {put_resp.text}"
                    logger.error(err_msg)
                    errors.append(err_msg)
                else:
                    processed_accounts += 1
                    total_transactions_synced += len(mapped_txs)
                
                # Small delay to avoid aggressive hits
                time.sleep(1)

        return _json_response({
            "status": "success",
            "user_id": user_id,
            "processed_accounts": processed_accounts,
            "total_transactions_synced": total_transactions_synced,
            "errors": errors
        })

    except Exception as e:
        logger.exception("Unexpected error during transaction sync")
        return _error(f"Internal server error: {str(e)}", status=500)


