import json
from typing import Any, Dict, Tuple

import functions_framework
from flask import Response, make_response
from google.cloud import firestore
from pydantic import ValidationError

# Support both "run as a package" (relative imports) and "run from this folder" (local imports).
try:  # pragma: no cover
    from .firestore_client import get_db
    from .models import UserCreate, UserUpdate
    from .serialization import user_doc_to_dict
except Exception:  # pragma: no cover
    from firestore_client import get_db
    from models import UserCreate, UserUpdate
    from serialization import user_doc_to_dict


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


@functions_framework.http
def users_api(request):
    """
    Cloud Function HTTP entry point for CRUD over the `users` collection.

    Paths:
      - GET    /users
      - POST   /users
      - GET    /users/{user_id}
      - PUT    /users/{user_id}
      - PATCH  /users/{user_id}
      - DELETE /users/{user_id}
    """

    if request.method == "OPTIONS":
        return _json_response({}, status=204)

    path = request.path or "/"
    parts = [p for p in path.split("/") if p]

    if not parts:
        return _json_response(
            {
                "service": "users_api",
                "endpoints": [
                    "GET /users",
                    "POST /users",
                    "GET /users/{user_id}",
                    "PUT/PATCH /users/{user_id}",
                    "DELETE /users/{user_id}",
                ],
            }
        )

    if parts[0] != "users":
        return _error("Not found", 404)

    db = get_db()
    users_ref = db.collection("users")

    # /users
    if len(parts) == 1:
        if request.method == "GET":
            docs = users_ref.stream()
            users = [user_doc_to_dict(d.id, d.to_dict() or {}) for d in docs]
            return _json_response({"users": users})

        if request.method == "POST":
            body, err = _parse_json(request)
            if err:
                return err
            if body is None:
                return _error("JSON body required", 400)
            try:
                payload = UserCreate.model_validate(body)
            except ValidationError as e:
                return _error("Validation error", 400, {"details": e.errors()})

            doc_ref = users_ref.document(payload.user_id)
            if doc_ref.get().exists:
                return _error("User already exists", 409)

            now = firestore.SERVER_TIMESTAMP
            doc_ref.set(
                {
                    "user_id": payload.user_id,
                    "username": payload.username,
                    "mono_token": payload.mono_token,
                    "active": payload.active,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            created = doc_ref.get()
            return _json_response(
                {"user": user_doc_to_dict(created.id, created.to_dict() or {})}, status=201
            )

        return _error("Method not allowed", 405)

    # /users/{user_id}
    if len(parts) == 2:
        user_id = parts[1]
        doc_ref = users_ref.document(user_id)

        if request.method == "GET":
            doc = doc_ref.get()
            if not doc.exists:
                return _error("User not found", 404)
            return _json_response({"user": user_doc_to_dict(doc.id, doc.to_dict() or {})})

        if request.method in ("PUT", "PATCH"):
            body, err = _parse_json(request)
            if err:
                return err
            if body is None:
                return _error("JSON body required", 400)
            try:
                payload = UserUpdate.model_validate(body)
            except ValidationError as e:
                return _error("Validation error", 400, {"details": e.errors()})

            doc = doc_ref.get()
            if not doc.exists:
                return _error("User not found", 404)

            updates: Dict[str, Any] = {}
            # Important: allow explicitly clearing nullable fields by sending `null`.
            # Use `model_fields_set` to distinguish missing vs provided-as-null.
            if "username" in payload.model_fields_set:
                updates["username"] = payload.username
            if "mono_token" in payload.model_fields_set:
                updates["mono_token"] = payload.mono_token
            if "active" in payload.model_fields_set:
                if payload.active is None:
                    return _error("`active` cannot be null", 400)
                updates["active"] = payload.active
            updates["updated_at"] = firestore.SERVER_TIMESTAMP

            if len(updates) == 1:  # only updated_at
                return _error("No updatable fields provided", 400)

            doc_ref.update(updates)
            updated = doc_ref.get()
            return _json_response(
                {"user": user_doc_to_dict(updated.id, updated.to_dict() or {})}
            )

        if request.method == "DELETE":
            doc = doc_ref.get()
            if not doc.exists:
                return _error("User not found", 404)
            doc_ref.delete()
            return _json_response({"deleted": True, "user_id": user_id})

        return _error("Method not allowed", 405)

    return _error("Not found", 404)


