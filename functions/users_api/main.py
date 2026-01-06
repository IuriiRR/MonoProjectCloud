import json
import os
import logging
import html
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
from typing import Any, Dict, Tuple

import functions_framework
from flask import Response, make_response

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
try:  # pragma: no cover
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    class _FirestoreShim:
        SERVER_TIMESTAMP = object()

    firestore = _FirestoreShim()  # type: ignore[assignment]
from pydantic import ValidationError

# Support both "run as a package" (relative imports) and "run from this folder" (local imports).
try:  # pragma: no cover
    from .auth import INTERNAL_UID, authenticate_request
    from .firestore_client import get_db
    from .models import UserCreate, UserUpdate
    from .serialization import user_doc_to_dict
except Exception:  # pragma: no cover
    from auth import INTERNAL_UID, authenticate_request
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


def _html_response(html: str, status: int = 200) -> Response:
    resp = make_response(html, status)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


def _sha256_hex(s: str) -> str:
    return sha256(s.encode("utf-8")).hexdigest()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _http_json(url: str, *, method: str = "GET", headers: Dict[str, str] | None = None, body: Any | None = None) -> Any:
    """
    Minimal JSON HTTP client (stdlib only).
    - body is JSON-encoded when provided
    - returns parsed JSON on 2xx; raises ValueError otherwise
    """
    import urllib.error
    import urllib.request

    hdrs: Dict[str, str] = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)

    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs["Content-Type"] = "application/json; charset=utf-8"

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise ValueError(f"HTTP {e.code} {url}: {raw}") from e


def _split_telegram_message(text: str, *, max_len: int = 3900) -> list[str]:
    """
    Telegram hard-limit is 4096 chars per message. We keep a safety margin.
    Prefer splitting on newlines to avoid breaking formatting (e.g. HTML tags).
    """
    t = text or ""
    if not t:
        return ["(empty report)"]

    lines = t.split("\n")
    chunks: list[str] = []
    cur = ""

    for line in lines:
        candidate = line if not cur else (cur + "\n" + line)
        if len(candidate) <= max_len:
            cur = candidate
            continue

        if cur:
            chunks.append(cur)
            cur = line
        else:
            # A single line is too long. Hard-split it.
            rest = line
            while len(rest) > max_len:
                chunks.append(rest[:max_len])
                rest = rest[max_len:]
            cur = rest

    if cur:
        chunks.append(cur)
    return chunks or ["(empty report)"]


def _render_inline_md_to_telegram_html(s: str) -> str:
    """
    Minimal markdown -> Telegram HTML converter for our report markdown.
    Supports:
      - `code` -> <code>code</code>
      - **bold** -> <b>bold</b>
    Everything else is HTML-escaped.
    """
    out: list[str] = []
    i = 0
    n = len(s or "")
    while i < n:
        next_code = s.find("`", i)
        next_bold = s.find("**", i)
        nexts = [p for p in (next_code, next_bold) if p != -1]
        if not nexts:
            out.append(html.escape(s[i:]))
            break

        j = min(nexts)
        if j > i:
            out.append(html.escape(s[i:j]))
            i = j
            continue

        if s.startswith("`", i):
            end = s.find("`", i + 1)
            if end == -1:
                out.append(html.escape(s[i:]))
                break
            out.append(f"<code>{html.escape(s[i + 1:end])}</code>")
            i = end + 1
            continue

        if s.startswith("**", i):
            end = s.find("**", i + 2)
            if end == -1:
                out.append(html.escape(s[i:]))
                break
            out.append(f"<b>{html.escape(s[i + 2:end])}</b>")
            i = end + 2
            continue

        # Fallback (shouldn't happen, but avoid infinite loops).
        out.append(html.escape(s[i]))
        i += 1

    return "".join(out)


def _report_markdown_to_telegram_html(report_md: str) -> str:
    """
    Convert our daily report markdown into Telegram-compatible HTML.
    Telegram HTML supports only a subset of tags (e.g. <b>, <i>, <code>, <pre>).
    """
    lines_out: list[str] = []
    for raw in (report_md or "").splitlines():
        line = (raw or "").rstrip()
        if not line:
            lines_out.append("")
            continue

        if line.startswith("## "):
            title = line[3:].strip()
            lines_out.append(f"🧾 <b>{html.escape(title)}</b>")
            continue

        if line.startswith("### "):
            title = line[4:].strip()
            emoji = "📝"
            if title.lower().startswith("spends"):
                emoji = "💸"
            elif title.lower().startswith("earnings"):
                emoji = "💰"
            lines_out.append(f"{emoji} <b>{html.escape(title)}</b>")
            continue

        prefix = ""
        content = line
        if content.startswith("- "):
            prefix = "• "
            content = content[2:]
        elif content.startswith("  - "):
            prefix = "  ◦ "
            content = content[4:]

        lines_out.append(prefix + _render_inline_md_to_telegram_html(content))

    # Avoid leading/trailing whitespace-only noise.
    return "\n".join(lines_out).strip() or "(empty report)"


def _telegram_send_message(bot_token: str, chat_id: int, text: str, *, parse_mode: str | None = None) -> None:
    # Telegram hard-limit is 4096 chars per message.
    chunks = _split_telegram_message(text, max_len=3900)
    for chunk in chunks:
        body: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        }
        if parse_mode:
            body["parse_mode"] = parse_mode
        _http_json(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            method="POST",
            body=body,
        )


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

    # Public Telegram callback endpoint (no auth): /telegram/connect?token=...&telegram_id=...
    if parts and parts[0] == "telegram":
        if len(parts) == 1:
            return _json_response(
                {
                    "service": "users_api",
                    "endpoints": ["GET /telegram/connect?token=...&telegram_id=..."],
                }
            )

        if len(parts) == 2 and parts[1] == "connect":
            if request.method != "GET":
                return _error("Method not allowed", 405)

            token = (request.args.get("token") or "").strip()
            telegram_id_raw = (request.args.get("telegram_id") or "").strip()
            if not token:
                return _html_response("<h3>Missing token</h3>", 400)
            try:
                telegram_id = int(telegram_id_raw)
            except Exception:
                return _html_response("<h3>Invalid telegram_id</h3>", 400)

            db = get_db()
            users_ref = db.collection("users")
            token_hash = _sha256_hex(token)

            docs = list(users_ref.where("telegram_connect_token_hash", "==", token_hash).limit(1).stream())
            if not docs:
                return _html_response(
                    "<h3>Invalid or expired link</h3><p>Please re-connect from the web interface.</p>",
                    400,
                )

            user_doc = docs[0]
            user_id = user_doc.id
            data = user_doc.to_dict() or {}
            expires_at = data.get("telegram_connect_expires_at")
            try:
                if expires_at and hasattr(expires_at, "timestamp"):
                    if expires_at.timestamp() < _now_utc().timestamp():
                        users_ref.document(user_id).update(
                            {
                                "telegram_connect_token_hash": None,
                                "telegram_connect_expires_at": None,
                                "updated_at": firestore.SERVER_TIMESTAMP,
                            }
                        )
                        return _html_response(
                            "<h3>Link expired</h3><p>Please re-connect from the web interface.</p>",
                            400,
                        )
            except Exception:
                return _html_response(
                    "<h3>Invalid link</h3><p>Please re-connect from the web interface.</p>",
                    400,
                )

            users_ref.document(user_id).update(
                {
                    "telegram_id": telegram_id,
                    "daily_report": True,
                    "telegram_connect_token_hash": None,
                    "telegram_connect_expires_at": None,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }
            )

            return _html_response(
                "<h3>Connected!</h3><p>Telegram reports are now enabled. You can disable them later in the web interface.</p>",
                200,
            )

        return _error("Not found", 404)

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
                    "POST /users/{user_id}/telegram/connect/init",
                    "POST /users/{user_id}/telegram/reports/daily/send",
                    "GET /telegram/connect?token=...&telegram_id=...",
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
            uid, auth_err, auth_status = authenticate_request(request)
            if auth_err:
                return _json_response(auth_err, status=auth_status or 401)
            if uid != INTERNAL_UID:
                return _error("Forbidden", 403, {"code": "FORBIDDEN"})

            docs = users_ref.stream()
            users = [user_doc_to_dict(d.id, d.to_dict() or {}) for d in docs]
            return _json_response({"users": users})

        if request.method == "POST":
            uid, auth_err, auth_status = authenticate_request(request)
            if auth_err:
                return _json_response(auth_err, status=auth_status or 401)

            body, err = _parse_json(request)
            if err:
                return err
            if body is None:
                return _error("JSON body required", 400)
            try:
                payload = UserCreate.model_validate(body)
            except ValidationError as e:
                return _error("Validation error", 400, {"details": e.errors()})

            if uid != INTERNAL_UID and payload.user_id != uid:
                return _error("Forbidden", 403, {"code": "FORBIDDEN"})

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
                    "telegram_id": payload.telegram_id,
                    "daily_report": payload.daily_report,
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
            uid, auth_err, auth_status = authenticate_request(request)
            if auth_err:
                return _json_response(auth_err, status=auth_status or 401)
            if uid != INTERNAL_UID and uid != user_id:
                return _error("Forbidden", 403, {"code": "FORBIDDEN"})

            doc = doc_ref.get()
            if not doc.exists:
                # UX requirement: authenticated user who is not registered in DB should get 403.
                if uid == INTERNAL_UID:
                    return _error("User not found", 404)
                return _error("User not found, please, register first", 403, {"code": "USER_NOT_FOUND"})
            return _json_response({"user": user_doc_to_dict(doc.id, doc.to_dict() or {})})

        if request.method in ("PUT", "PATCH"):
            uid, auth_err, auth_status = authenticate_request(request)
            if auth_err:
                return _json_response(auth_err, status=auth_status or 401)
            if uid != INTERNAL_UID and uid != user_id:
                return _error("Forbidden", 403, {"code": "FORBIDDEN"})

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
                if uid == INTERNAL_UID:
                    return _error("User not found", 404)
                return _error("User not found, please, register first", 403, {"code": "USER_NOT_FOUND"})

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
            if "telegram_id" in payload.model_fields_set:
                updates["telegram_id"] = payload.telegram_id
            if "daily_report" in payload.model_fields_set:
                if payload.daily_report is None:
                    return _error("`daily_report` cannot be null", 400)
                updates["daily_report"] = payload.daily_report
            updates["updated_at"] = firestore.SERVER_TIMESTAMP

            if len(updates) == 1:  # only updated_at
                return _error("No updatable fields provided", 400)

            doc_ref.update(updates)
            updated = doc_ref.get()
            return _json_response(
                {"user": user_doc_to_dict(updated.id, updated.to_dict() or {})}
            )

        if request.method == "DELETE":
            uid, auth_err, auth_status = authenticate_request(request)
            if auth_err:
                return _json_response(auth_err, status=auth_status or 401)
            if uid != INTERNAL_UID and uid != user_id:
                return _error("Forbidden", 403, {"code": "FORBIDDEN"})

            doc = doc_ref.get()
            if not doc.exists:
                if uid == INTERNAL_UID:
                    return _error("User not found", 404)
                return _error("User not found, please, register first", 403, {"code": "USER_NOT_FOUND"})
            doc_ref.delete()
            return _json_response({"deleted": True, "user_id": user_id})

        return _error("Method not allowed", 405)

    # /users/{user_id}/telegram/connect/init
    if len(parts) == 5 and parts[0] == "users" and parts[2] == "telegram" and parts[3] == "connect" and parts[4] == "init":
        user_id = parts[1]
        if request.method != "POST":
            return _error("Method not allowed", 405)

        uid, auth_err, auth_status = authenticate_request(request)
        if auth_err:
            return _json_response(auth_err, status=auth_status or 401)
        if uid != INTERNAL_UID and uid != user_id:
            return _error("Forbidden", 403, {"code": "FORBIDDEN"})

        doc_ref = users_ref.document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            if uid == INTERNAL_UID:
                return _error("User not found", 404)
            return _error("User not found, please, register first", 403, {"code": "USER_NOT_FOUND"})

        bot_username = (os.getenv("TELEGRAM_BOT_USERNAME") or "").strip().lstrip("@")
        if not bot_username:
            return _error("Server misconfigured: TELEGRAM_BOT_USERNAME is not set", 500)

        token = secrets.token_urlsafe(32)
        token_hash = _sha256_hex(token)
        expires_at = _now_utc() + timedelta(minutes=30)
        doc_ref.update(
            {
                "telegram_connect_token_hash": token_hash,
                "telegram_connect_expires_at": expires_at,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
        )

        bot_url = f"https://t.me/{bot_username}?start={token}"
        return _json_response({"bot_url": bot_url, "expires_at": expires_at.isoformat()})

    # /users/{user_id}/telegram/reports/daily/send
    if (
        len(parts) == 6
        and parts[0] == "users"
        and parts[2] == "telegram"
        and parts[3] == "reports"
        and parts[4] == "daily"
        and parts[5] == "send"
    ):
        user_id = parts[1]
        if request.method != "POST":
            return _error("Method not allowed", 405)

        uid, auth_err, auth_status = authenticate_request(request)
        if auth_err:
            return _json_response(auth_err, status=auth_status or 401)
        if uid != INTERNAL_UID and uid != user_id:
            return _error("Forbidden", 403, {"code": "FORBIDDEN"})

        bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
        if not bot_token:
            return _error("Server misconfigured: TELEGRAM_BOT_TOKEN is not set", 500)

        report_api_url = (os.getenv("REPORT_API_URL") or "").strip()
        if not report_api_url:
            return _error("Server misconfigured: REPORT_API_URL is not set", 500)

        internal_key = (os.getenv("INTERNAL_API_KEY") or "").strip()
        if not internal_key:
            return _error("Server misconfigured: INTERNAL_API_KEY is not set", 500)

        doc_ref = users_ref.document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            if uid == INTERNAL_UID:
                return _error("User not found", 404)
            return _error("User not found, please, register first", 403, {"code": "USER_NOT_FOUND"})

        user_data = doc.to_dict() or {}
        telegram_id = user_data.get("telegram_id")
        if telegram_id is None:
            return _error(
                "Telegram is not connected. Connect Telegram reports first.",
                400,
                {"code": "TELEGRAM_NOT_CONNECTED"},
            )
        try:
            telegram_id_int = int(telegram_id)
        except Exception:
            return _error("Invalid telegram_id stored for user", 500)

        if not bool(user_data.get("daily_report", False)):
            return _error(
                "Telegram reports are disabled. Enable them in Settings first.",
                400,
                {"code": "TELEGRAM_REPORTS_DISABLED"},
            )

        body, err = _parse_json(request)
        if err:
            return err
        body = body or {}
        date = (body.get("date") or "").strip() or None
        tz = (body.get("tz") or "").strip() or None
        llm = body.get("llm")

        from urllib.parse import urlencode

        qs: Dict[str, str] = {}
        if date:
            qs["date"] = date
        if tz:
            qs["tz"] = tz
        if llm is False:
            qs["llm"] = "0"
        url = f"{report_api_url}/users/{user_id}/reports/daily"
        if qs:
            url = f"{url}?{urlencode(qs)}"

        try:
            report_payload = _http_json(url, method="GET", headers={"X-Internal-Api-Key": internal_key})
        except Exception as e:
            return _error("Failed to fetch daily report", 500, {"details": str(e)})

        report_md = ""
        if isinstance(report_payload, dict):
            report_md = str(report_payload.get("report_markdown") or "")
        if not report_md:
            report_md = "Daily report is empty."

        try:
            pretty_html = _report_markdown_to_telegram_html(report_md)
            _telegram_send_message(bot_token, telegram_id_int, pretty_html, parse_mode="HTML")
        except Exception as e:
            return _error("Failed to send Telegram message", 500, {"details": str(e)})

        return _json_response({"sent": True})

    return _error("Not found", 404)


