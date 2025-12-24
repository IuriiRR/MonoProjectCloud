from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class SyncRequest(BaseModel):
    user_id: Optional[str] = None  # If provided, sync only this user. Otherwise all.

class SyncResponse(BaseModel):
    status: str
    processed_users: int
    total_accounts_synced: int
    errors: List[str] = []

