import json
from typing import Any, Dict, Tuple

import functions_framework
from flask import Response, make_response
from google.cloud import firestore
from pydantic import ValidationError

# Support both "run as a package" (relative imports) and "run from this folder" (local imports).
try:  # pragma: no cover
    from .firestore_client import get_db
    from .models import AccountCreate, AccountUpdate
    from .serialization import account_doc_to_dict
except Exception:  # pragma: no cover
    from firestore_client import get_db
    from models import AccountCreate, AccountUpdate
    from serialization import account_doc_to_dict


def _json_response(payload: Any, status: int = 200) -> Response:
    resp = make_response(json.dumps(payload, ensure_ascii=False), status)
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    # CORS (local dev convenience)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp


def _error(message: str, status: int = 400, extra: Dict[str, Any] | None = None) -> Response:
    body: Dict[str, Any] = {"error": message}
    if extra:
        body.update(extra)
    return _json_response(body, status=status)


def _parse_json(request) -> Tuple[Dict[str, Any] | None, Response | None]:
    if not request.data:
        return None, None
    try:
        return request.get_json(silent=False), None
    except Exception:
        return None, _error("Invalid JSON body", 400)


def _require_user(db, user_id: str):
    users_ref = db.collection("users")
    user_ref = users_ref.document(user_id)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return None, _error("User not found", 404)
    return user_ref, None


@functions_framework.http
def accounts_api(request):
    """
    Cloud Function HTTP entry point for CRUD over `users/{user_id}/accounts`.

    Paths:
      - GET    /users/{user_id}/accounts
      - POST   /users/{user_id}/accounts
      - GET    /users/{user_id}/accounts/{account_id}
      - PUT    /users/{user_id}/accounts/{account_id}
      - PATCH  /users/{user_id}/accounts/{account_id}
      - DELETE /users/{user_id}/accounts/{account_id}
    """

    if request.method == "OPTIONS":
        return _json_response({}, status=204)

    path = request.path or "/"
    parts = [p for p in path.split("/") if p]

    if not parts:
        return _json_response(
            {
                "service": "accounts_api",
                "endpoints": [
                    "GET /users/{user_id}/accounts",
                    "POST /users/{user_id}/accounts",
                    "GET /users/{user_id}/accounts/{account_id}",
                    "PUT/PATCH /users/{user_id}/accounts/{account_id}",
                    "DELETE /users/{user_id}/accounts/{account_id}",
                ],
            }
        )

    if parts[0] != "users":
        return _error("Not found", 404)

    if len(parts) < 3 or parts[2] != "accounts":
        return _error("Not found", 404)

    user_id = parts[1]

    db = get_db()
    _, user_err = _require_user(db, user_id)
    if user_err:
        return user_err

    accounts_ref = db.collection("users").document(user_id).collection("accounts")

    # /users/{user_id}/accounts
    if len(parts) == 3:
        if request.method == "GET":
            docs = accounts_ref.stream()
            accounts = [account_doc_to_dict(d.id, d.to_dict() or {}) for d in docs]
            return _json_response({"accounts": accounts})

        if request.method == "POST":
            body, err = _parse_json(request)
            if err:
                return err
            if body is None:
                return _error("JSON body required", 400)
            try:
                payload = AccountCreate.model_validate(body)
            except ValidationError as e:
                return _error("Validation error", 400, {"details": e.errors()})

            doc_ref = accounts_ref.document(payload.id)
            if doc_ref.get().exists:
                return _error("Account already exists", 409)

            now = firestore.SERVER_TIMESTAMP
            doc_ref.set(
                {
                    "id": payload.id,
                    "type": payload.type,
                    "send_id": payload.send_id,
                    "currency": payload.currency,
                    "balance": payload.balance,
                    "is_active": payload.is_active,
                    "title": payload.title,
                    "goal": payload.goal,
                    "is_budget": payload.is_budget,
                    "invested": payload.invested,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            created = doc_ref.get()
            return _json_response(
                {"account": account_doc_to_dict(created.id, created.to_dict() or {})},
                status=201,
            )

        return _error("Method not allowed", 405)

    # /users/{user_id}/accounts/{account_id}
    if len(parts) == 4:
        account_id = parts[3]
        doc_ref = accounts_ref.document(account_id)

        if request.method == "GET":
            doc = doc_ref.get()
            if not doc.exists:
                return _error("Account not found", 404)
            return _json_response(
                {"account": account_doc_to_dict(doc.id, doc.to_dict() or {})}
            )

        if request.method in ("PUT", "PATCH"):
            body, err = _parse_json(request)
            if err:
                return err
            if body is None:
                return _error("JSON body required", 400)
            try:
                payload = AccountUpdate.model_validate(body)
            except ValidationError as e:
                return _error("Validation error", 400, {"details": e.errors()})

            doc = doc_ref.get()
            if not doc.exists:
                return _error("Account not found", 404)

            updates: Dict[str, Any] = {}
            # Allow explicitly clearing nullable fields by sending `null`.
            if "type" in payload.model_fields_set:
                if payload.type is None:
                    return _error("`type` cannot be null", 400)
                updates["type"] = payload.type
            if "send_id" in payload.model_fields_set:
                updates["send_id"] = payload.send_id
            if "currency" in payload.model_fields_set:
                if payload.currency is None:
                    return _error("`currency` cannot be null", 400)
                updates["currency"] = payload.currency
            if "balance" in payload.model_fields_set:
                if payload.balance is None:
                    return _error("`balance` cannot be null", 400)
                updates["balance"] = payload.balance
            if "is_active" in payload.model_fields_set:
                if payload.is_active is None:
                    return _error("`is_active` cannot be null", 400)
                updates["is_active"] = payload.is_active
            if "title" in payload.model_fields_set:
                updates["title"] = payload.title
            if "goal" in payload.model_fields_set:
                updates["goal"] = payload.goal
            if "is_budget" in payload.model_fields_set:
                if payload.is_budget is None:
                    return _error("`is_budget` cannot be null", 400)
                updates["is_budget"] = payload.is_budget
            if "invested" in payload.model_fields_set:
                if payload.invested is None:
                    return _error("`invested` cannot be null", 400)
                updates["invested"] = payload.invested

            updates["updated_at"] = firestore.SERVER_TIMESTAMP

            if len(updates) == 1:  # only updated_at
                return _error("No updatable fields provided", 400)

            doc_ref.update(updates)
            updated = doc_ref.get()
            return _json_response(
                {"account": account_doc_to_dict(updated.id, updated.to_dict() or {})}
            )

        if request.method == "DELETE":
            doc = doc_ref.get()
            if not doc.exists:
                return _error("Account not found", 404)
            doc_ref.delete()
            return _json_response({"deleted": True, "account_id": account_id})

        return _error("Method not allowed", 405)

    return _error("Not found", 404)


