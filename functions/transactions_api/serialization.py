from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()


def transaction_doc_to_dict(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": data.get("id") or doc_id,
        "time": data.get("time"),
        "description": data.get("description"),
        "amount": data.get("amount"),
        "operation_amount": data.get("operation_amount"),
        "commission_rate": data.get("commission_rate"),
        "cashback_amount": data.get("cashback_amount"),
        "balance": data.get("balance"),
        "hold": data.get("hold", False),
        "comment": data.get("comment"),
        "mcc_code": data.get("mcc_code"),
        "original_mcc": data.get("original_mcc"),
        "currency": data.get("currency"),
        "created_at": _dt_to_iso(data.get("created_at")),
        "updated_at": _dt_to_iso(data.get("updated_at")),
    }



