from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field

Number = Union[int, float]


class AccountCreate(BaseModel):
    # Document ID under users/{user_id}/accounts
    id: str = Field(min_length=1)

    # Common fields
    type: Literal["jar", "card"]
    send_id: Optional[str] = None
    currency: Dict[str, Any]
    balance: Number
    is_active: bool = True

    # Jar-only fields
    title: Optional[str] = None
    goal: Optional[Number] = None

    # App-owned fields (must be preserved by sync)
    is_budget: bool = False
    invested: Number = 0


class AccountUpdate(BaseModel):
    # PATCH/PUT style (partial updates). Any provided field is updated.
    type: Optional[Literal["jar", "card"]] = None
    send_id: Optional[str] = None
    currency: Optional[Dict[str, Any]] = None
    balance: Optional[Number] = None
    is_active: Optional[bool] = None
    title: Optional[str] = None
    goal: Optional[Number] = None
    is_budget: Optional[bool] = None
    invested: Optional[Number] = None


