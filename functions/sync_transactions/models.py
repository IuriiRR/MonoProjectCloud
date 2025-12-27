from typing import List, Optional
from pydantic import BaseModel

class SyncTransactionsRequest(BaseModel):
    user_id: str
    mono_token: str
    days: int = 30 # Default to 30 days of history

class SyncTransactionsResponse(BaseModel):
    status: str
    user_id: str
    processed_accounts: int
    total_transactions_synced: int
    errors: List[str] = []


