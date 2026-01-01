import json
import os
import logging
from hashlib import sha256
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import functions_framework
from flask import Response, make_response, request

logging.basicConfig(level=logging.INFO)

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
    from .llm_team import maybe_refine_and_write_report_with_llm
    from .matching import Tx, match_spends_to_earnings
    from .models import DailyReportRequest, DailyReportResponse, SpendCoverage
    from .render import render_markdown_report
except Exception:  # pragma: no cover
    from auth import INTERNAL_UID, authenticate_request
    from firestore_client import get_db
    from llm_team import maybe_refine_and_write_report_with_llm
    from matching import Tx, match_spends_to_earnings
    from models import DailyReportRequest, DailyReportResponse, SpendCoverage
    from render import render_markdown_report


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


def _require_user(db, user_id: str, *, is_internal: bool):
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    if not user_doc.exists:
        if is_internal:
            return None, _error("User not found", 404)
        return None, _error("User not found, please, register first", 403, {"code": "USER_NOT_FOUND"})
    return user_ref, None


def _get_tz(tz_name: str) -> timezone:
    # We only need a tzinfo for formatting + day boundaries. Use zoneinfo if available.
    try:  # pragma: no cover
        from zoneinfo import ZoneInfo  # py3.9+

        return ZoneInfo(tz_name)  # type: ignore[return-value]
    except Exception:
        return timezone.utc


def _parse_day_window(date_str: Optional[str], tz_name: str) -> Tuple[str, int, int, timezone]:
    tzinfo = _get_tz(tz_name)
    if date_str is None:
        now = datetime.now(tz=tzinfo)
        date_str = now.strftime("%Y-%m-%d")
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        raise ValueError("Invalid date format, expected YYYY-MM-DD")
    start_local = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=tzinfo)
    end_local = start_local + timedelta(days=1) - timedelta(seconds=1)
    return date_str, int(start_local.timestamp()), int(end_local.timestamp()), tzinfo


def _fetch_accounts_map(db, user_id: str) -> Dict[str, Dict[str, Any]]:
    accounts_ref = db.collection("users").document(user_id).collection("accounts")
    out: Dict[str, Dict[str, Any]] = {}
    for d in accounts_ref.stream():
        out[d.id] = d.to_dict() or {}
    return out


def _fetch_transactions_for_day(db, user_id: str, start_ts: int, end_ts: int) -> list[Dict[str, Any]]:
    query = (
        db.collection_group("transactions")
        .where("user_id", "==", user_id)
        .where("time", ">=", start_ts)
        .where("time", "<=", end_ts)
        .order_by("time", direction=firestore.Query.ASCENDING)
    )
    docs = query.stream()
    txs: list[Dict[str, Any]] = []
    for d in docs:
        data = d.to_dict() or {}
        data["id"] = data.get("id") or d.id
        txs.append(data)
    return txs


def _txs_hash_for_cache(raw_txs: list[Dict[str, Any]]) -> str:
    # Stable hash of the transaction set that impacts coverage/report.
    # Keep only fields relevant to matching/report; sort for stability.
    simplified = []
    for t in raw_txs:
        simplified.append(
            {
                "id": str(t.get("id") or ""),
                "time": int(t.get("time") or 0),
                "amount": int(t.get("amount") or 0),
                "description": str(t.get("description") or ""),
                "account_id": str(t.get("account_id") or ""),
            }
        )
    simplified.sort(key=lambda x: (x["time"], x["id"]))
    return sha256(json.dumps(simplified, ensure_ascii=False).encode("utf-8")).hexdigest()


def _get_report_cache_doc(db, user_id: str, *, date: str, tz: str) -> str:
    safe_tz = tz.replace("/", "_")
    return f"daily_{date}_{safe_tz}"


@functions_framework.http
def report_api(request):
    """
    Cloud Function HTTP entry point for daily transactions reports.

    Paths:
      - GET /users/{user_id}/reports/daily?date=YYYY-MM-DD&tz=Europe/Kyiv&llm=1
    """
    try:
        if request.method == "OPTIONS":
            return _json_response({}, status=204)

        path = request.path or "/"
        parts = [p for p in path.split("/") if p]

        if not parts:
            return _json_response(
                {
                    "service": "report_api",
                    "endpoints": ["GET /users/{user_id}/reports/daily?date=YYYY-MM-DD&tz=Europe/Kyiv&llm=1"],
                }
            )

        if parts[0] != "users":
            return _error("Not found", 404)
        if len(parts) != 4 or parts[2] != "reports" or parts[3] != "daily":
            return _error("Not found", 404)
        if request.method != "GET":
            return _error("Method not allowed", 405)

        user_id = parts[1]

        uid, auth_err, auth_status = authenticate_request(request)
        if auth_err:
            return _json_response(auth_err, status=auth_status or 401)
        is_internal = uid == INTERNAL_UID
        if not is_internal and uid != user_id:
            return _error("Forbidden", 403, {"code": "FORBIDDEN"})

        db = get_db()
        _, user_err = _require_user(db, user_id, is_internal=is_internal)
        if user_err:
            return user_err

        tz_name = request.args.get("tz") or os.getenv("REPORT_TIMEZONE") or "Europe/Kyiv"
        req_date = request.args.get("date")
        llm_flag = (request.args.get("llm") or "1").strip().lower()
        llm_enabled = llm_flag not in ("0", "false", "no", "off")

        date_str, start_ts, end_ts, tzinfo = _parse_day_window(req_date, tz_name)

        raw_txs = _fetch_transactions_for_day(db, user_id, start_ts, end_ts)
        accounts_by_id = _fetch_accounts_map(db, user_id)
        tx_hash = _txs_hash_for_cache(raw_txs)

        # Firestore cache to avoid repeated LLM calls (and speed up UI refresh).
        cache_id = _get_report_cache_doc(db, user_id, date=date_str, tz=tz_name)
        cache_ref = db.collection("users").document(user_id).collection("reports_cache").document(cache_id)
        cache_doc = cache_ref.get()
        if cache_doc.exists:
            cached = cache_doc.to_dict() or {}
            if cached.get("tx_hash") == tx_hash:
                cached_llm_used = bool(cached.get("llm_used"))
                # If caller doesn't want LLM, any cache is fine. If caller wants LLM, require llm_used cache.
                if (not llm_enabled) or cached_llm_used:
                    payload = cached.get("payload")
                    if isinstance(payload, dict):
                        return _json_response(payload, status=200)

        txs: list[Tx] = []
        for t in raw_txs:
            amount_raw = t.get("amount") or 0
            try:
                amount_cents = int(amount_raw)
            except Exception:
                # fallback for weird numeric formats
                amount_cents = int(float(amount_raw))
            txs.append(
                Tx(
                    id=str(t.get("id") or ""),
                    time=int(t.get("time") or 0),
                    amount_cents=amount_cents,
                    description=str(t.get("description") or ""),
                )
            )

        matches, _earn_remaining = match_spends_to_earnings(txs)

        fallback_md = render_markdown_report(
            date=date_str,
            tz_name=tz_name,
            tzinfo=tzinfo,
            txs=txs,
            matches=matches,
            accounts_by_id=accounts_by_id,
        )

        uncovered_exists = any(not m.covered for m in matches)
        should_call_llm = llm_enabled and (uncovered_exists or (request.args.get("llm") or "").lower() == "full")

        if should_call_llm:
            llm_res = maybe_refine_and_write_report_with_llm(
                txs=txs,
                initial_matches=matches,
                fallback_markdown=fallback_md,
            )
            final_matches = llm_res.refined_matches or matches
            report_md = llm_res.report_markdown
            report_html = llm_res.report_html
            llm_used = True
        else:
            final_matches = matches
            report_md = fallback_md
            report_html = None
            llm_used = False

        spends = [t for t in txs if t.amount_cents < 0]
        earns = [t for t in txs if t.amount_cents > 0]
        spend_total = sum(-t.amount_cents for t in spends)
        earn_total = sum(t.amount_cents for t in earns)
        net = earn_total - spend_total

        spends_payload: list[SpendCoverage] = []
        for m in final_matches:
            spends_payload.append(
                SpendCoverage(
                    tx_id=m.spend_tx_id,
                    covered=m.covered,
                    covered_cents=m.covered_cents,
                    uncovered_cents=m.uncovered_cents,
                    sources=[{"tx_id": sid, "amount_cents": amt} for (sid, amt) in m.sources],
                    reason=None if m.covered else "Not fully compensated by same-day earnings",
                )
            )

        # Allow body validation for future POST expansion, but today we are GET-only.
        try:
            _ = DailyReportRequest.model_validate({"date": req_date})
        except ValidationError:
            return _error("Invalid request", 400)

        resp_model = DailyReportResponse(
            user_id=user_id,
            date=date_str,
            timezone=tz_name,
            totals={"spend_total": spend_total, "earn_total": earn_total, "net": net},
            spends=spends_payload,
            report_markdown=report_md,
            report_html=report_html,
        )
        payload = resp_model.model_dump()

        # Cache the response (best-effort; ignore write errors).
        try:
            cache_ref.set(
                {
                    "tx_hash": tx_hash,
                    "llm_used": llm_used,
                    "payload": payload,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
        except Exception:
            pass

        return _json_response(payload, status=200)

    except FailedPrecondition as e:
        return _error("Firestore query requires an index", 400, {"details": str(e)})
    except ValueError as e:
        return _error(str(e), 400)
    except Exception as e:
        return _error("Internal server error", 500, {"details": str(e)})

