import os
from typing import Any, Dict, Optional, Tuple

try:  # pragma: no cover
    import firebase_admin
    from firebase_admin import auth as firebase_auth
except Exception:  # pragma: no cover
    firebase_admin = None  # type: ignore[assignment]
    firebase_auth = None  # type: ignore[assignment]

INTERNAL_UID = "__internal__"


def _is_truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in ("1", "true", "yes", "on")


def is_auth_disabled() -> bool:
    return _is_truthy(os.getenv("AUTH_DISABLED")) or os.getenv("AUTH_MODE", "enabled").lower() == "disabled"


def _internal_auth_ok(headers) -> bool:
    internal_key = os.getenv("INTERNAL_API_KEY")
    if not internal_key:
        return False
    presented = headers.get("X-Internal-Api-Key") or headers.get("X-Internal-API-Key")
    return presented == internal_key


def _init_firebase() -> None:
    if firebase_admin is None:
        raise RuntimeError("firebase-admin is not installed")

    try:
        firebase_admin.get_app()
        return
    except ValueError:
        pass

    project_id = (
        os.getenv("FIRESTORE_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCP_PROJECT")
    )
    options = {"projectId": project_id} if project_id else None
    firebase_admin.initialize_app(options=options)


def authenticate_request(request) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[int]]:
    if _internal_auth_ok(request.headers):
        return INTERNAL_UID, None, None

    if is_auth_disabled():
        return os.getenv("DEV_UID", "dev-user"), None, None

    authz = request.headers.get("Authorization", "")
    if not authz.startswith("Bearer "):
        return None, {"error": "Missing Authorization header", "code": "UNAUTHENTICATED"}, 401

    token = authz.split(" ", 1)[1].strip()
    if not token:
        return None, {"error": "Missing bearer token", "code": "UNAUTHENTICATED"}, 401

    if firebase_admin is None or firebase_auth is None:
        return None, {"error": "Auth verification unavailable", "code": "AUTH_UNAVAILABLE"}, 500

    _init_firebase()
    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception as e:
        return None, {"error": "Invalid auth token", "code": "INVALID_TOKEN", "details": str(e)}, 401

    uid = decoded.get("uid") or decoded.get("user_id") or decoded.get("sub")
    if not uid:
        return None, {"error": "Invalid auth token (missing uid)", "code": "INVALID_TOKEN"}, 401

    return uid, None, None


