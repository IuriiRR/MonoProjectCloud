import json
import os
import logging
from typing import Any, Dict, Tuple

import functions_framework
from flask import Response, make_response, request
try:  # pragma: no cover
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    class _FirestoreShim:
        SERVER_TIMESTAMP = object()

        class Query:
            ASCENDING = "ASCENDING"
            DESCENDING = "DESCENDING"

    firestore = _FirestoreShim()  # type: ignore[assignment]

try:  # pragma: no cover
    from google.api_core.exceptions import FailedPrecondition  # type: ignore
except Exception:  # pragma: no cover
    FailedPrecondition = Exception  # type: ignore
from pydantic import ValidationError

logging.basicConfig(level=logging.INFO)

# Optional Sentry
def _is_truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in ("1", "true", "yes", "on")


def _init_sentry() -> None:
    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if not dsn or _is_truthy(os.getenv("DISABLE_SENTRY")):
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.gcp import GcpIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[GcpIntegration()],
            send_default_pii=True,
            enable_logs=True,
            traces_sample_rate=1.0,
            profile_session_sample_rate=1.0,
            profile_lifecycle="trace",
        )
    except Exception:
        # Never fail the function due to Sentry init issues.
        return


_init_sentry()

# Support both "run as a package" (relative imports) and "run from this folder" (local imports).
try:  # pragma: no cover
    from .auth import INTERNAL_UID, authenticate_request
    from .firestore_client import get_db
    from .models import TransactionCreate, TransactionUpdate
    from .serialization import transaction_doc_to_dict
except Exception:  # pragma: no cover
    from auth import INTERNAL_UID, authenticate_request
    from firestore_client import get_db
    from models import TransactionCreate, TransactionUpdate
    from serialization import transaction_doc_to_dict


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


def _require_account(db, user_id: str, account_id: str):
    account_ref = db.collection("users").document(user_id).collection("accounts").document(account_id)
    account_doc = account_ref.get()
    if not account_doc.exists:
        return None, _error("Account not found", 404)
    return account_ref, None


def _require_user(db, user_id: str, *, is_internal: bool):
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    if not user_doc.exists:
        if is_internal:
            return None, _error("User not found", 404)
        return None, _error("User not found, please, register first", 403, {"code": "USER_NOT_FOUND"})
    return user_ref, None


@functions_framework.http
def transactions_api(request):
    """
    Cloud Function HTTP entry point for CRUD over `users/{user_id}/accounts/{account_id}/transactions`.

    Paths:
      - GET    /users/{user_id}/accounts/{account_id}/transactions
      - POST   /users/{user_id}/accounts/{account_id}/transactions
      - GET    /users/{user_id}/accounts/{account_id}/transactions/{transaction_id}
      - PUT    /users/{user_id}/accounts/{account_id}/transactions/{transaction_id}
      - PATCH  /users/{user_id}/accounts/{account_id}/transactions/{transaction_id}
      - DELETE /users/{user_id}/accounts/{account_id}/transactions/{transaction_id}
    """

    try:
        if request.method == "OPTIONS":
            return _json_response({}, status=204)

        path = request.path or "/"
        parts = [p for p in path.split("/") if p]

        if not parts:
            return _json_response(
                {
                    "service": "transactions_api",
                    "endpoints": [
                        "GET /transactions",
                        "GET /users/{user_id}/transactions",
                        "GET /users/{user_id}/charts/balance",
                        "GET /users/{user_id}/accounts/{account_id}/transactions",
                        "POST /users/{user_id}/accounts/{account_id}/transactions",
                        "GET /users/{user_id}/accounts/{account_id}/transactions/{transaction_id}",
                        "PUT/PATCH /users/{user_id}/accounts/{account_id}/transactions/{transaction_id}",
                        "DELETE /users/{user_id}/accounts/{account_id}/transactions/{transaction_id}",
                    ],
                }
            )

        db = get_db()

        # GET /transactions (Global collection group query)
        if len(parts) == 1 and parts[0] == "transactions":
            if request.method == "GET":
                uid, auth_err, auth_status = authenticate_request(request)
                if auth_err:
                    return _json_response(auth_err, status=auth_status or 401)
                if uid != INTERNAL_UID:
                    return _error("Forbidden", 403, {"code": "FORBIDDEN"})

                query = db.collection_group("transactions").order_by(
                    "time", direction=firestore.Query.DESCENDING
                )

                # Optional filters
                since = request.args.get("since")
                if since and since.isdigit():
                    query = query.where("time", ">=", int(since))

                time_gte = request.args.get("time_gte")
                if time_gte and time_gte.isdigit():
                    query = query.where("time", ">=", int(time_gte))

                limit = request.args.get("limit")
                if limit and limit.isdigit():
                    query = query.limit(int(limit))

                docs = query.stream()
                transactions = []
                for d in docs:
                    data = d.to_dict() or {}
                    # Fallback for old data: extract user_id and account_id from document path
                    # Path: users/{user_id}/accounts/{account_id}/transactions/{transaction_id}
                    if "user_id" not in data or "account_id" not in data:
                        path_parts = d.reference.path.split("/")
                        if len(path_parts) >= 4:
                            data["user_id"] = data.get("user_id") or path_parts[1]
                            data["account_id"] = data.get("account_id") or path_parts[3]

                    transactions.append(transaction_doc_to_dict(d.id, data))

                return _json_response({"transactions": transactions})
            return _error("Method not allowed", 405)

        if parts[0] != "users":
            return _error("Not found", 404)

        user_id = parts[1]
        uid, auth_err, auth_status = authenticate_request(request)
        if auth_err:
            return _json_response(auth_err, status=auth_status or 401)
        is_internal = uid == INTERNAL_UID
        if not is_internal and uid != user_id:
            return _error("Forbidden", 403, {"code": "FORBIDDEN"})

        _, user_err = _require_user(db, user_id, is_internal=is_internal)
        if user_err:
            return user_err

        # GET /users/{user_id}/transactions
        if len(parts) == 3 and parts[2] == "transactions":
            if request.method == "GET":
                query = (
                    db.collection_group("transactions")
                    .where("user_id", "==", user_id)
                    .order_by("time", direction=firestore.Query.DESCENDING)
                )

                limit = request.args.get("limit")
                if limit and limit.isdigit():
                    query = query.limit(int(limit))

                docs = query.stream()
                transactions = [transaction_doc_to_dict(d.id, d.to_dict() or {}) for d in docs]
                return _json_response({"transactions": transactions})
            return _error("Method not allowed", 405)

        # GET /users/{user_id}/charts/balance
        if len(parts) == 4 and parts[2] == "charts" and parts[3] == "balance":
            if request.method == "GET":
                # Fetch all transactions for the user to build the chart
                query = (
                    db.collection_group("transactions")
                    .where("user_id", "==", user_id)
                    .order_by("time", direction=firestore.Query.ASCENDING)
                )

                docs = query.stream()

                # Structure data for charts: { account_id: [ {time, balance}, ... ] }
                chart_data: Dict[str, list] = {}
                for d in docs:
                    data = d.to_dict() or {}
                    acc_id = data.get("account_id")
                    if not acc_id:
                        continue

                    if acc_id not in chart_data:
                        chart_data[acc_id] = []

                    chart_data[acc_id].append({"time": data.get("time"), "balance": data.get("balance")})

                return _json_response({"charts": chart_data})
            return _error("Method not allowed", 405)

        if len(parts) < 5 or parts[2] != "accounts" or parts[4] != "transactions":
            return _error("Not found", 404)

        user_id = parts[1]
        account_id = parts[3]

        _, acc_err = _require_account(db, user_id, account_id)
        if acc_err:
            return acc_err

        transactions_ref = (
            db.collection("users")
            .document(user_id)
            .collection("accounts")
            .document(account_id)
            .collection("transactions")
        )

        # /users/{user_id}/accounts/{account_id}/transactions
        if len(parts) == 5:
            if request.method == "GET":
                # Sorting by time desc by default
                query = transactions_ref.order_by("time", direction=firestore.Query.DESCENDING)

                # Optional filters
                since = request.args.get("since")
                if since and since.isdigit():
                    query = query.where("time", ">=", int(since))

                time_gte = request.args.get("time_gte")
                if time_gte and time_gte.isdigit():
                    query = query.where("time", ">=", int(time_gte))

                limit = request.args.get("limit")
                if limit and limit.isdigit():
                    query = query.limit(int(limit))

                docs = query.stream()
                transactions = [transaction_doc_to_dict(d.id, d.to_dict() or {}) for d in docs]
                return _json_response({"transactions": transactions})

            if request.method == "POST":
                body, err = _parse_json(request)
                if err:
                    return err
                if body is None:
                    return _error("JSON body required", 400)

                # Inject denormalized IDs from path if missing from body
                if "user_id" not in body:
                    body["user_id"] = user_id
                if "account_id" not in body:
                    body["account_id"] = account_id

                try:
                    payload = TransactionCreate.model_validate(body)
                except ValidationError as e:
                    return _error("Validation error", 400, {"details": e.errors()})

                doc_ref = transactions_ref.document(payload.id)
                if doc_ref.get().exists:
                    return _error("Transaction already exists", 409)

                now = firestore.SERVER_TIMESTAMP
                data = payload.model_dump()
                data["created_at"] = now
                data["updated_at"] = now

                doc_ref.set(data)
                created = doc_ref.get()
                return _json_response(
                    {"transaction": transaction_doc_to_dict(created.id, created.to_dict() or {})},
                    status=201,
                )

            if request.method == "PUT":
                body, err = _parse_json(request)
                if err:
                    return err
                if body is None or "transactions" not in body or not isinstance(body["transactions"], list):
                    return _error("JSON body with 'transactions' list required", 400)

                transactions_data = body["transactions"]
                batch = db.batch()
                now = firestore.SERVER_TIMESTAMP
                processed_ids = []

                for i, item in enumerate(transactions_data):
                    # Inject denormalized IDs from path if missing from body
                    if "user_id" not in item:
                        item["user_id"] = user_id
                    if "account_id" not in item:
                        item["account_id"] = account_id

                    try:
                        payload = TransactionCreate.model_validate(item)
                        doc_ref = transactions_ref.document(payload.id)

                        data = payload.model_dump()
                        data["created_at"] = now
                        data["updated_at"] = now

                        # Use set with merge=True for "duplicate skipping tolerance" (upsert)
                        batch.set(doc_ref, data, merge=True)
                        processed_ids.append(payload.id)
                    except ValidationError as e:
                        return _error(f"Validation error at index {i}", 400, {"details": e.errors()})

                batch.commit()
                return _json_response({"processed": len(processed_ids), "ids": processed_ids})

            return _error("Method not allowed", 405)

        # /users/{user_id}/accounts/{account_id}/transactions/{transaction_id}
        if len(parts) == 6:
            transaction_id = parts[5]
            doc_ref = transactions_ref.document(transaction_id)

            if request.method == "GET":
                doc = doc_ref.get()
                if not doc.exists:
                    return _error("Transaction not found", 404)
                return _json_response(
                    {"transaction": transaction_doc_to_dict(doc.id, doc.to_dict() or {})}
                )

            if request.method in ("PUT", "PATCH"):
                body, err = _parse_json(request)
                if err:
                    return err
                if body is None:
                    return _error("JSON body required", 400)
                try:
                    payload = TransactionUpdate.model_validate(body)
                except ValidationError as e:
                    return _error("Validation error", 400, {"details": e.errors()})

                doc = doc_ref.get()
                if not doc.exists:
                    return _error("Transaction not found", 404)

                updates: Dict[str, Any] = {}
                # Use model_fields_set to allow explicit nulls if needed, though most transaction fields are non-nullable in Monobank
                for field in payload.model_fields_set:
                    updates[field] = getattr(payload, field)

                if not updates:
                    return _error("No updatable fields provided", 400)

                updates["updated_at"] = firestore.SERVER_TIMESTAMP
                doc_ref.update(updates)
                updated = doc_ref.get()
                return _json_response(
                    {"transaction": transaction_doc_to_dict(updated.id, updated.to_dict() or {})}
                )

            if request.method == "DELETE":
                doc = doc_ref.get()
                if not doc.exists:
                    return _error("Transaction not found", 404)
                doc_ref.delete()
                return _json_response({"deleted": True, "transaction_id": transaction_id})

            return _error("Method not allowed", 405)

        return _error("Not found", 404)
    except FailedPrecondition as e:
        # Firestore missing index errors usually show up as FailedPrecondition in production.
        return _error("Firestore query requires an index", 400, {"details": str(e)})
    except Exception as e:
        # Always return JSON + CORS, so browsers don't report CORS failures on 500s.
        return _error("Internal server error", 500, {"details": str(e)})


