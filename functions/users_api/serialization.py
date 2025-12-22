from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    # Firestore timestamps are tz-aware; normalize to ISO 8601.
    return dt.isoformat()


def user_doc_to_dict(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    # Ensure stable, API-friendly JSON (timestamps -> strings).
    return {
        "user_id": data.get("user_id") or doc_id,
        "username": data.get("username"),
        "mono_token": data.get("mono_token"),
        "active": data.get("active", True),
        "created_at": _dt_to_iso(data.get("created_at")),
        "updated_at": _dt_to_iso(data.get("updated_at")),
    }





