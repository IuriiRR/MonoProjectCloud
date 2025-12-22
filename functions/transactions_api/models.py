from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field

Number = Union[int, float]


class TransactionCreate(BaseModel):
    # Document ID under users/{user_id}/accounts/{account_id}/transactions
    id: str = Field(min_length=1)

    # Monobank statement item fields (MVP)
    time: int
    description: Optional[str] = None
    amount: Number
    operation_amount: Optional[Number] = None
    commission_rate: Optional[Number] = None
    cashback_amount: Optional[Number] = None
    balance: Number
    hold: bool = False
    comment: Optional[str] = None
    mcc_code: Optional[int] = None
    original_mcc: Optional[int] = None
    currency: Dict[str, Any]


class TransactionUpdate(BaseModel):
    # PATCH/PUT style (partial updates). Any provided field is updated.
    time: Optional[int] = None
    description: Optional[str] = None
    amount: Optional[Number] = None
    operation_amount: Optional[Number] = None
    commission_rate: Optional[Number] = None
    cashback_amount: Optional[Number] = None
    balance: Optional[Number] = None
    hold: Optional[bool] = None
    comment: Optional[str] = None
    mcc_code: Optional[int] = None
    original_mcc: Optional[int] = None
    currency: Optional[Dict[str, Any]] = None



