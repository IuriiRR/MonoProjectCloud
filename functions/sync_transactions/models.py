from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class SyncTransactionsRequest(BaseModel):
    user_id: str
    mono_token: str
    days: int = 30 # Default to 30 days of history
    accounts: Optional[List[Dict[str, Any]]] = None

class SyncTransactionsResponse(BaseModel):
    status: str
    user_id: str
    processed_accounts: int
    total_transactions_synced: int
    errors: List[str] = []


