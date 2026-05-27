import logging
from typing import List
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
        logger.error(f"Failed to initialize Firestore: {e}")
        return None

def sync_sql_to_firestore():
    """
    Pushes local SQL data to Cloud Firestore. 
    Useful if the Pi goes offline and the cloud failover takes over.
    """
    db = get_firestore_client()
    if not db:
        return
        
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        for user in users:
            user_ref = db.collection("users").document(user.user_id)
            user_ref.set({
                "user_id": user.user_id,
                "username": user.username,
                "mono_token": user.mono_token,
                "active": user.active,
            }, merge=True)
            
            # Sync accounts
            accounts = session.exec(select(Account).where(Account.user_id == user.user_id)).all()
            for account in accounts:
                acc_ref = user_ref.collection("accounts").document(account.id)
                acc_ref.set({
                    "id": account.id,
                    "type": account.type,
                    "balance": account.balance,
                    "is_active": account.is_active,
                }, merge=True)
                
            logger.info(f"Synced user {user.user_id} to Firestore")

def sync_firestore_to_sql():
    """
    Pulls Cloud Firestore data into local SQL database.
    Useful for initializing the local DB or restoring state.
    """
    db = get_firestore_client()
    if not db:
        return
    logger.info("Firestore to SQL sync not yet fully implemented")
    pass
