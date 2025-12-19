from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()


def account_doc_to_dict(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": data.get("id") or doc_id,
        "type": data.get("type"),
        "send_id": data.get("send_id"),
        "currency": data.get("currency"),
        "balance": data.get("balance"),
        "is_active": data.get("is_active", True),
        "title": data.get("title"),
        "goal": data.get("goal"),
        "is_budget": data.get("is_budget", False),
        "invested": data.get("invested", 0),
        "created_at": _dt_to_iso(data.get("created_at")),
        "updated_at": _dt_to_iso(data.get("updated_at")),
    }


