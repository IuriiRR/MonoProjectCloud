from typing import List, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    user_id: str = Field(min_length=1)
    mono_token: Optional[str] = None
    username: Optional[str] = None
    active: bool = True
    # Telegram integration
    telegram_id: Optional[int] = None
    daily_report: bool = False
    # Family integration
    family_members: List[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    # PATCH/PUT style (partial updates). Any provided field is updated.
    mono_token: Optional[str] = None
    username: Optional[str] = None
    active: Optional[bool] = None
    # Telegram integration
    telegram_id: Optional[int] = None
    daily_report: Optional[bool] = None
    # Family integration
    # We generally don't update family_members directly via PUT/PATCH, 
    # but via specific endpoints, but good to have in model if we ever need it.
    # However, for safety, maybe exclude it from general update to prevent accidental overrides?
    # The current implementation of PATCH in main.py blindly updates fields if present in model.
    # Let's keep it out of UserUpdate for now to enforce using specific endpoints.
