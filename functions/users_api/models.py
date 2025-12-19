from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    user_id: str = Field(min_length=1)
    mono_token: Optional[str] = None
    username: Optional[str] = None
    active: bool = True


class UserUpdate(BaseModel):
    # PATCH/PUT style (partial updates). Any provided field is updated.
    mono_token: Optional[str] = None
    username: Optional[str] = None
    active: Optional[bool] = None


