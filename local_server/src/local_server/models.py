from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class User(SQLModel, table=True):
    user_id: str = Field(primary_key=True)
    username: Optional[str] = None
    mono_token: str
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    accounts: List["Account"] = Relationship(back_populates="user")

class Account(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="user.user_id")
    type: str = Field(default="jar")  # "jar" or "card"
    send_id: Optional[str] = None
    currency_code: int = Field(default=980) # UAH
    balance: int = Field(default=0)
    is_active: bool = Field(default=True)
    
    # Jar specific fields
    title: Optional[str] = None
    goal: Optional[int] = None
    is_budget: bool = Field(default=False)
    invested: int = Field(default=0)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: Optional[User] = Relationship(back_populates="accounts")
    transactions: List["Transaction"] = Relationship(back_populates="account")

class Transaction(SQLModel, table=True):
    id: str = Field(primary_key=True)
    account_id: str = Field(foreign_key="account.id")
    user_id: str = Field(index=True) # Redundant for fast querying by user
    time: int = Field(index=True)
    description: Optional[str] = None
    amount: int
    operation_amount: Optional[int] = None
    commission_rate: Optional[int] = None
    cashback_amount: Optional[int] = None
    balance: int
    hold: bool = Field(default=False)
    comment: Optional[str] = None
    mcc_code: Optional[int] = None
    original_mcc: Optional[int] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    account: Optional[Account] = Relationship(back_populates="transactions")
