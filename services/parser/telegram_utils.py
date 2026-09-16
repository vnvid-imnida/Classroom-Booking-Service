# Uses PEP 8
# Tools: black, flake8, mypy

"""Telegram Bot API delivery for parser notifications (mirrors backend/telegram_utils)."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


class TelegramSendError(RuntimeError):
    """Raised when a Telegram message cannot be delivered."""


def _telegram_enabled() -> bool:
    raw = os.getenv("TELEGRAM_NOTIFY_ENABLED", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def send_telegram_message(*, chat_id: int | str, text: str) -> None:
    """Send a plain-text message via Telegram Bot API (or log when disabled)."""
    if chat_id is None or str(chat_id).strip() == "":
        logger.info("Skip Telegram — empty chat_id")
        return

    chat_id = str(chat_id).strip()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    if not _telegram_enabled():
        msg = f"TELEGRAM_NOTIFY_ENABLED=false — to={chat_id}\n{text}"
        print(msg, flush=True)
        logger.info(msg)
        return

    if not token or token.startswith("YOUR_") or "changeme" in token.lower():
        msg = f"TELEGRAM_BOT_TOKEN unset — would notify {chat_id}: {text[:120]}"
        print(msg, flush=True)
        logger.info(msg)
        return

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        api_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body) if body else {}
            if not data.get("ok", False):
                raise TelegramSendError(f"Telegram API error: {body[:300]}")
            logger.info("Telegram message sent to chat_id=%s", chat_id)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise TelegramSendError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise TelegramSendError(str(exc.reason or exc)) from exc
