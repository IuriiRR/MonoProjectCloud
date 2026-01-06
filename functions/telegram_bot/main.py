import json
import os
import logging
from typing import Any, Dict, Optional

import functions_framework
from flask import Response, make_response

logging.basicConfig(level=logging.INFO)


def _json_response(payload: Any, status: int = 200) -> Response:
    resp = make_response(json.dumps(payload, ensure_ascii=False), status)
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,X-Telegram-Bot-Api-Secret-Token"
    return resp


def _error(message: str, status: int = 400, extra: Dict[str, Any] | None = None) -> Response:
    body: Dict[str, Any] = {"error": message}
    if extra:
        body.update(extra)
    return _json_response(body, status=status)


def _http_json(url: str, *, method: str = "GET", headers: Dict[str, str] | None = None, body: Any | None = None) -> Any:
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
        # Polling uses Telegram long-polling (timeout=25s). Keep our client timeout comfortably above that.
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            ct = (resp.headers.get("content-type") or "").lower()
            if "application/json" in ct:
                return json.loads(raw) if raw else None
            # Some endpoints (e.g. our local /telegram/connect) return HTML.
            return raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise ValueError(f"HTTP {e.code} {url}: {raw}") from e


def _telegram_send_message(bot_token: str, chat_id: int, text: str, *, reply_markup: Optional[dict] = None) -> None:
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        _http_json(f"https://api.telegram.org/bot{bot_token}/sendMessage", method="POST", body=payload)
    except Exception as e:
        # Never crash the bot loop due to Telegram API hiccups.
        logging.exception("Telegram sendMessage failed: %s", e)


def _telegram_answer_callback(bot_token: str, callback_query_id: str, text: str | None = None, *, show_alert: bool = False) -> None:
    payload: Dict[str, Any] = {"callback_query_id": callback_query_id, "show_alert": show_alert}
    if text:
        payload["text"] = text
    try:
        _http_json(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", method="POST", body=payload)
    except Exception as e:
        logging.exception("Telegram answerCallbackQuery failed: %s", e)


def _extract_start_token(message_text: str) -> Optional[str]:
    # Telegram provides "/start <payload>" (payload is optional).
    t = (message_text or "").strip()
    if not t.startswith("/start"):
        return None
    parts = t.split(maxsplit=1)
    if len(parts) == 2 and parts[1].strip():
        return parts[1].strip()
    return ""


def _validate_secret(request) -> bool:
    expected = (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()
    if not expected:
        return True
    presented = (request.headers.get("X-Telegram-Bot-Api-Secret-Token") or "").strip()
    return presented == expected


def _handle_update(update: Dict[str, Any]) -> None:
    bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    users_api_url = (os.getenv("USERS_API_URL") or "").strip()
    if not bot_token or not users_api_url:
        logging.error("Missing TELEGRAM_BOT_TOKEN or USERS_API_URL")
        return

    # Handle callback button presses (connect flow without external URL; required for local dev).
    cb = update.get("callback_query")
    if isinstance(cb, dict):
        cb_id = str(cb.get("id") or "")
        data = str(cb.get("data") or "")
        msg = cb.get("message") or {}
        chat = (msg.get("chat") or {}) if isinstance(msg, dict) else {}
        chat_id = chat.get("id")
        try:
            chat_id_int = int(chat_id)
        except Exception:
            chat_id_int = None

        if data.startswith("connect|") and chat_id_int is not None:
            token = data.split("|", 1)[1].strip()
            if not token:
                _telegram_answer_callback(bot_token, cb_id, "Missing token", show_alert=True)
                return
            try:
                _http_json(
                    f"{users_api_url}/telegram/connect?token={token}&telegram_id={chat_id_int}",
                    method="GET",
                )
                _telegram_answer_callback(bot_token, cb_id, "Connected!", show_alert=False)
                _telegram_send_message(bot_token, chat_id_int, "Connected! You can disable reports later in the web interface.")
            except Exception as e:
                logging.exception("Connect call failed: %s", e)
                _telegram_answer_callback(bot_token, cb_id, "Failed to connect. Try again from Settings.", show_alert=True)
            return

        if cb_id:
            _telegram_answer_callback(bot_token, cb_id)
        return

    msg = update.get("message") or update.get("edited_message")
    if not isinstance(msg, dict):
        return

    text = str(msg.get("text") or "")
    start_payload = _extract_start_token(text)
    if start_payload is None:
        return

    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    try:
        chat_id_int = int(chat_id)
    except Exception:
        return

    if start_payload:
        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "Connect reports monohelper",
                        "callback_data": f"connect|{start_payload}",
                    }
                ]
            ]
        }
        _telegram_send_message(
            bot_token,
            chat_id_int,
            "It will connect this bot to your account. You can deactivate reports later in web interface.",
            reply_markup=reply_markup,
        )
    else:
        _telegram_send_message(
            bot_token,
            chat_id_int,
            "Open Settings in the web interface and click “Connect Telegram reports” to generate a link.",
        )


@functions_framework.http
def telegram_bot(request):
    """
    Telegram bot webhook handler.

    - In prod: configure Telegram webhook to this function URL.
    - In dev: use polling helper in polling.py (or set webhook to local tunnel).
    """
    if request.method == "OPTIONS":
        return _json_response({}, status=204)

    if request.method == "GET":
        return _json_response(
            {
                "service": "telegram_bot",
                "mode": "webhook",
                "note": "POST Telegram updates here",
            }
        )

    if request.method != "POST":
        return _error("Method not allowed", 405)

    if not _validate_secret(request):
        # Most common cause: webhook secret configured in env, but Telegram webhook was set without secret_token.
        logging.warning("Forbidden: invalid Telegram webhook secret token header")
        return _error("Forbidden (invalid telegram secret)", 403)

    try:
        update = request.get_json(silent=False) or {}
    except Exception:
        return _error("Invalid JSON body", 400)

    try:
        if isinstance(update, dict):
            _handle_update(update)
    except Exception as e:
        logging.exception("Failed to handle Telegram update: %s", e)
        # Telegram expects 200 even if we had internal issues, otherwise it retries aggressively.
        return _json_response({"ok": True}, status=200)

    return _json_response({"ok": True}, status=200)

