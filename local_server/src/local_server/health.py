from datetime import datetime, timezone

from flask import Flask

_state = {"last_heartbeat_at": None, "last_error": None}


def mark_heartbeat() -> None:
    _state["last_heartbeat_at"] = datetime.now(timezone.utc).isoformat()
    _state["last_error"] = None


def mark_error(message: str) -> None:
    _state["last_error"] = message


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return {
            "status": "ok",
            "last_heartbeat_at": _state["last_heartbeat_at"],
            "last_error": _state["last_error"],
        }, 200

    return app
