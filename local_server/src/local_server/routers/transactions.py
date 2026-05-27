from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from local_server.database import get_session
from local_server.models import Transaction

router = APIRouter()

@router.get("/")
def list_transactions(
    user_id: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=1000),
    session: Session = Depends(get_session),
):
    q = select(Transaction).order_by(Transaction.time.desc())  # type: ignore[arg-type]
    if user_id:
        q = q.where(Transaction.user_id == user_id)
    if account_id:
        q = q.where(Transaction.account_id == account_id)
    q = q.limit(limit)
    transactions = session.exec(q).all()
    return {"transactions": transactions}
