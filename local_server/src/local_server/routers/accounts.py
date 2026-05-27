from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from local_server.database import get_session
from local_server.models import Account

router = APIRouter()

@router.get("/")
def list_accounts(
    user_id: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
):
    q = select(Account)
    if user_id:
        q = q.where(Account.user_id == user_id)
    accounts = session.exec(q).all()
    return {"accounts": accounts}
