import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from local_server.database import get_session
from local_server.models import Account, Transaction, User
from local_server.sync_firestore import sync_firestore_to_sql

logger = logging.getLogger(__name__)

MONO_API_URL = "https://api.monobank.ua"

router = APIRouter()


class SyncTransactionsRequest(BaseModel):
    user_id: Optional[str] = None
    days: int = 30


@router.post("/accounts")
def sync_accounts(session: Session = Depends(get_session)):
    users = session.exec(
        select(User).where(User.active == True, User.mono_token != "")
    ).all()

    processed_users = 0
    total_accounts_synced = 0
    errors = []

    for user in users:
        resp = requests.get(
            f"{MONO_API_URL}/personal/client-info",
            headers={"X-Token": user.mono_token},
            timeout=30,
        )
        if not resp.ok:
            msg = f"Monobank error for user {user.user_id}: {resp.text}"
            logger.error(msg)
            errors.append(msg)
            continue

        data = resp.json()
        now = datetime.now(timezone.utc)
        count = 0

        for acc in data.get("accounts", []):
            session.merge(Account(
                id=acc["id"],
                user_id=user.user_id,
                type="card",
                send_id=acc.get("sendId"),
                currency_code=int(acc.get("currencyCode", 980)),
                balance=int(acc.get("balance", 0)),
                is_active=True,
                updated_at=now,
            ))
            count += 1

        for jar in data.get("jars", []):
            session.merge(Account(
                id=jar["id"],
                user_id=user.user_id,
                type="jar",
                send_id=jar.get("sendId"),
                currency_code=int(jar.get("currencyCode", 980)),
                balance=int(jar.get("balance", 0)),
                is_active=True,
                title=jar.get("title"),
                goal=jar.get("goal"),
                updated_at=now,
            ))
            count += 1

        session.commit()
        processed_users += 1
        total_accounts_synced += count
        logger.info("Synced %d accounts for user %s", count, user.user_id)

    return {
        "status": "success",
        "processed_users": processed_users,
        "total_accounts_synced": total_accounts_synced,
        "errors": errors,
    }


@router.post("/transactions")
def sync_transactions(
    body: SyncTransactionsRequest = SyncTransactionsRequest(),
    session: Session = Depends(get_session),
):
    to_time = int(time.time())
    from_time = to_time - body.days * 24 * 3600

    if body.user_id:
        user = session.get(User, body.user_id)
        if not user:
            return {"status": "error", "error": f"User {body.user_id} not found"}
        accounts = session.exec(
            select(Account).where(Account.user_id == body.user_id)
        ).all()
        token_map = {body.user_id: user.mono_token}
    else:
        accounts = session.exec(select(Account)).all()
        users = session.exec(select(User)).all()
        token_map = {u.user_id: u.mono_token for u in users}

    processed_accounts = 0
    total_transactions_synced = 0
    errors = []

    for account in accounts:
        mono_token = token_map.get(account.user_id)
        if not mono_token:
            continue

        url = f"{MONO_API_URL}/personal/statement/{account.id}/{from_time}/{to_time}"
        success = False
        resp: requests.Response | None = None
        for _ in range(2):
            resp = requests.get(url, headers={"X-Token": mono_token}, timeout=60)
            if resp.status_code == 429:
                logger.warning("Rate limited by Monobank, waiting 60s...")
                time.sleep(60)
                continue
            if not resp.ok:
                msg = f"Monobank statement error for account {account.id}: {resp.text}"
                logger.error(msg)
                errors.append(msg)
                break
            success = True
            break

        if not success or resp is None:
            continue

        txs = resp.json() or []
        now = datetime.now(timezone.utc)
        for tx in txs:
            session.merge(Transaction(
                id=tx["id"],
                account_id=account.id,
                user_id=account.user_id,
                time=int(tx["time"]),
                description=tx.get("description"),
                amount=int(tx["amount"]),
                operation_amount=tx.get("operationAmount"),
                commission_rate=tx.get("commissionRate"),
                cashback_amount=tx.get("cashbackAmount"),
                balance=int(tx["balance"]),
                hold=bool(tx.get("hold", False)),
                comment=tx.get("comment"),
                mcc_code=tx.get("mcc"),
                original_mcc=tx.get("originalMcc"),
                updated_at=now,
            ))

        session.commit()
        processed_accounts += 1
        total_transactions_synced += len(txs)
        logger.info("Synced %d transactions for account %s", len(txs), account.id)
        time.sleep(1)

    return {
        "status": "success",
        "processed_accounts": processed_accounts,
        "total_transactions_synced": total_transactions_synced,
        "errors": errors,
    }


@router.post("/firestore")
def trigger_firestore_sync():
    """Pull all data from Cloud Firestore into local SQLite."""
    result = sync_firestore_to_sql()
    return result
