import logging
from datetime import datetime, timezone
from sqlmodel import Session, select
from local_server.database import engine
from local_server.models import User, Account, Transaction

try:
    from google.cloud import firestore
except ImportError:
    firestore = None

logger = logging.getLogger(__name__)


def get_firestore_client():
    if not firestore:
        logger.warning("Firestore client not installed.")
        return None
    try:
        return firestore.Client()
    except Exception as e:
        logger.error(f"Failed to initialize Firestore client: {e}")
        return None


_CURRENCY_CODES = {"UAH": 980, "USD": 840, "EUR": 978, "GBP": 826}

def _to_currency_code(value) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return _CURRENCY_CODES.get(str(value).upper(), 980)

def _parse_dt(value) -> datetime:
    """Convert Firestore Timestamp or datetime to UTC datetime."""
    if value is None:
        return datetime.now(timezone.utc)
    if hasattr(value, "ToDatetime"):
        return value.ToDatetime(tzinfo=timezone.utc)
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return datetime.now(timezone.utc)


def sync_firestore_to_sql() -> dict:
    """Pull Cloud Firestore data into local SQLite database."""
    db = get_firestore_client()
    if not db:
        return {"ok": False, "error": "Firestore client unavailable"}

    counts = {"users": 0, "accounts": 0, "transactions": 0}

    with Session(engine) as session:
        for user_doc in db.collection("users").stream():
            u = user_doc.to_dict()
            session.merge(User(
                user_id=u.get("user_id") or user_doc.id,
                username=u.get("username"),
                mono_token=u.get("mono_token") or "",
                active=bool(u.get("active", True)),
                created_at=_parse_dt(u.get("created_at")),
                updated_at=_parse_dt(u.get("updated_at")),
            ))
            counts["users"] += 1

            for acc_doc in db.collection("users").document(user_doc.id).collection("accounts").stream():
                a = acc_doc.to_dict()
                session.merge(Account(
                    id=a.get("id") or acc_doc.id,
                    user_id=user_doc.id,
                    type=a.get("type", "jar"),
                    send_id=a.get("send_id"),
                    currency_code=_to_currency_code((a.get("currency") or {}).get("code", 980)),
                    balance=int(a.get("balance", 0)),
                    is_active=bool(a.get("is_active", True)),
                    title=a.get("title"),
                    goal=a.get("goal"),
                    is_budget=bool(a.get("is_budget", False)),
                    invested=int(a.get("invested", 0)),
                    created_at=_parse_dt(a.get("created_at")),
                    updated_at=_parse_dt(a.get("updated_at")),
                ))
                counts["accounts"] += 1

                txn_col = (
                    db.collection("users")
                    .document(user_doc.id)
                    .collection("accounts")
                    .document(acc_doc.id)
                    .collection("transactions")
                )
                for txn_doc in txn_col.stream():
                    t = txn_doc.to_dict()
                    session.merge(Transaction(
                        id=t.get("id") or txn_doc.id,
                        account_id=t.get("account_id") or acc_doc.id,
                        user_id=t.get("user_id") or user_doc.id,
                        time=int(t.get("time", 0)),
                        description=t.get("description"),
                        amount=int(t.get("amount", 0)),
                        operation_amount=t.get("operation_amount"),
                        commission_rate=t.get("commission_rate"),
                        cashback_amount=t.get("cashback_amount"),
                        balance=int(t.get("balance", 0)),
                        hold=bool(t.get("hold", False)),
                        comment=t.get("comment"),
                        mcc_code=t.get("mcc_code"),
                        original_mcc=t.get("original_mcc"),
                        created_at=_parse_dt(t.get("created_at")),
                        updated_at=_parse_dt(t.get("updated_at")),
                    ))
                    counts["transactions"] += 1

        session.commit()

    logger.info("Firestore→SQL sync complete: %s", counts)
    return {"ok": True, "counts": counts}


def sync_sql_to_firestore() -> None:
    """Push local SQL data to Cloud Firestore (used after Pi reconnects)."""
    db = get_firestore_client()
    if not db:
        return

    with Session(engine) as session:
        for user in session.exec(select(User)).all():
            user_ref = db.collection("users").document(user.user_id)
            user_ref.set(
                {"user_id": user.user_id, "username": user.username, "mono_token": user.mono_token, "active": user.active},
                merge=True,
            )
            for account in session.exec(select(Account).where(Account.user_id == user.user_id)).all():
                acc_ref = user_ref.collection("accounts").document(account.id)
                acc_ref.set(
                    {"id": account.id, "type": account.type, "balance": account.balance, "is_active": account.is_active},
                    merge=True,
                )
            logger.info(f"Synced user {user.user_id} to Firestore")
