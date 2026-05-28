import calendar
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from local_server.database import get_session
from local_server.models import Account, Transaction

router = APIRouter()


class JarMonthlyReport(BaseModel):
    id: str
    title: Optional[str]
    current_balance: int
    start_balance: int
    budget: int
    total_deposits: int
    spent: int


class MonthlyReportResponse(BaseModel):
    month: str
    jars: list[JarMonthlyReport]


def _month_unix_range(month: str) -> tuple[int, int]:
    try:
        dt = datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid month format: '{month}'. Expected YYYY-MM.")
    _, last_day = calendar.monthrange(dt.year, dt.month)
    start = int(datetime(dt.year, dt.month, 1, tzinfo=timezone.utc).timestamp())
    end = int(datetime(dt.year, dt.month, last_day, 23, 59, 59, tzinfo=timezone.utc).timestamp()) + 1
    return start, end


@router.get("/monthly", response_model=MonthlyReportResponse)
def get_monthly_report(
    month: str = Query(..., description="Month in YYYY-MM format"),
    user_id: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> MonthlyReportResponse:
    month_start, month_end = _month_unix_range(month)

    q = select(Account).where(Account.is_budget == True)
    if user_id:
        q = q.where(Account.user_id == user_id)
    jars = session.exec(q).all()

    result = []
    for jar in jars:
        txs = session.exec(
            select(Transaction)
            .where(Transaction.account_id == jar.id)
            .where(Transaction.time >= month_start)
            .where(Transaction.time < month_end)
            .order_by(Transaction.time)  # type: ignore[arg-type]
        ).all()

        if txs:
            start_balance = txs[0].balance - txs[0].amount
        else:
            start_balance = jar.balance

        budget = max((tx.amount for tx in txs if tx.amount > 0), default=0)
        total_deposits = sum(tx.amount for tx in txs if tx.amount > 0)
        spent = sum(tx.amount for tx in txs) - budget

        result.append(JarMonthlyReport(
            id=jar.id,
            title=jar.title,
            current_balance=jar.balance,
            start_balance=start_balance,
            budget=budget,
            total_deposits=total_deposits,
            spent=spent,
        ))

    return MonthlyReportResponse(month=month, jars=result)
