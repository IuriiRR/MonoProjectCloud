"""
Local development helper: run the bot in polling mode.

Env vars:
  - TELEGRAM_BOT_TOKEN (required)
  - USERS_API_PUBLIC_URL (recommended) e.g. http://localhost:8081
  - USERS_API_URL (fallback)

Usage:
  python -m polling
"""

import json
import os
import time
from typing import Any, Dict, Optional

from main import _handle_update, _http_json


def _delete_webhook(bot_token: str) -> None:
    # Required for local polling if the bot previously had a webhook configured.
    # Otherwise Telegram returns: "Conflict: can't use getUpdates method while webhook is active"
    drop = (os.getenv("TELEGRAM_DROP_PENDING_UPDATES") or "").strip().lower() in ("1", "true", "yes", "on")
    qs = "?drop_pending_updates=true" if drop else ""
    _http_json(f"https://api.telegram.org/bot{bot_token}/deleteWebhook{qs}", method="POST")


def _get_updates(bot_token: str, offset: Optional[int]) -> Dict[str, Any]:
    qs = ""
    if offset is not None:
        qs = f"?offset={offset}&timeout=25"
    return _http_json(f"https://api.telegram.org/bot{bot_token}/getUpdates{qs}", method="GET") or {}


def run_polling() -> None:
    bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    users_api_url = (os.getenv("USERS_API_PUBLIC_URL") or os.getenv("USERS_API_URL") or "").strip()
    if not bot_token or not users_api_url:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN or USERS_API_PUBLIC_URL/USERS_API_URL")

    should_delete_webhook = (os.getenv("TELEGRAM_POLLING_DELETE_WEBHOOK") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if should_delete_webhook:
        try:
            _delete_webhook(bot_token)
        except Exception as e:
            print("Failed to deleteWebhook (polling may fail if webhook is active):", str(e))

    offset: Optional[int] = None
    print("Polling started. Press Ctrl+C to stop.")
    while True:
        try:
            payload = _get_updates(bot_token, offset)
        except TimeoutError:
            # Network hiccup / long-poll edge case. Just retry.
            continue
        except Exception as e:
            print("getUpdates exception:", str(e))
            time.sleep(2)
            continue
        if not payload.get("ok"):
            print("getUpdates error:", json.dumps(payload, ensure_ascii=False))
            time.sleep(2)
            continue

        updates = payload.get("result") or []
        for u in updates:
            if isinstance(u, dict):
                offset = int(u.get("update_id", 0)) + 1
                _handle_update(u)


if __name__ == "__main__":
    run_polling()

