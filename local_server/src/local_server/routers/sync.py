from fastapi import APIRouter
from local_server.sync_firestore import sync_firestore_to_sql

router = APIRouter()


@router.post("/accounts")
def sync_accounts():
    return {"status": "ok"}


@router.post("/transactions")
def sync_transactions():
    return {"status": "ok"}


@router.post("/firestore")
def trigger_firestore_sync():
    """Pull all data from Cloud Firestore into local SQLite."""
    result = sync_firestore_to_sql()
    return result
