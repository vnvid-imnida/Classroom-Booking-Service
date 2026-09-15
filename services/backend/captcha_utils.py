# Uses PEP 8
# Tools: black, flake8, mypy

"""Cloudflare Turnstile server-side verification."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def _turnstile_secret_key() -> str:
    return os.getenv("TURNSTILE_SECRET_KEY", "").strip()


def captcha_enabled() -> bool:
    """Return True when Turnstile secret is configured."""
    return bool(_turnstile_secret_key())


def verify_turnstile_token(token: str, remote_ip: str | None = None) -> bool:
    """Validate a Turnstile token with Cloudflare Siteverify API.

    Args:
        token: Client-side widget response token.
        remote_ip: Optional visitor IP for Cloudflare risk checks.

    Returns:
        True when Cloudflare reports ``success``.
    """
    secret = _turnstile_secret_key()
    if not token or not secret:
        return False

    payload: dict[str, str] = {
        "secret": secret,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        TURNSTILE_VERIFY_URL,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Turnstile verify request failed: %s", exc)
        return False

    if not body.get("success"):
        logger.info("Turnstile rejected token: %s", body.get("error-codes"))
    return body.get("success") is True
