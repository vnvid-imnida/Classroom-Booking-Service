# Uses PEP 8
# Tools: black, flake8, mypy

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "dev-change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "168"))
LINK_TOKEN_TTL_MINUTES = int(os.getenv("LINK_TOKEN_TTL_MINUTES", "30"))


def hash_password(password: str) -> str:
    """Hash a plaintext password with PBKDF2 and a random salt.

    Args:
        password: Plaintext password.

    Returns:
        Stored hash string in ``salt$hexdigest`` format.
    """
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a plaintext password against a stored PBKDF2 hash.

    Args:
        password: Plaintext password to verify.
        stored: Value previously returned by ``hash_password``.

    Returns:
        True if the password matches.
    """
    try:
        salt, digest_hex = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return secrets.compare_digest(digest.hex(), digest_hex)


def create_access_token(user_id: str) -> str:
    """Issue a signed JWT for the given user.

    Args:
        user_id: User UUID string (JWT subject).

    Returns:
        Encoded JWT access token.
    """
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode({"sub": user_id, "exp": exp}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Decode a JWT and return the subject user id.

    Args:
        token: Bearer access token.

    Returns:
        User id from the ``sub`` claim, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def new_link_token() -> str:
    """Generate a one-time token for Telegram account linking.

    Returns:
        URL-safe random token string.
    """
    return secrets.token_urlsafe(32)


def validate_telegram_webapp_init_data(init_data: str, bot_token: str) -> dict | None:
    """Validate Telegram Web App initData HMAC and parse the user payload.

    Args:
        init_data: Raw initData query string from the Web App.
        bot_token: Telegram bot token used to derive the secret key.

    Returns:
        Parsed Telegram user dict on success, otherwise None.
    """
    if not init_data or not bot_token:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        if not secrets.compare_digest(calculated, received_hash):
            return None
        user_raw = pairs.get("user")
        if not user_raw:
            return None
        return json.loads(user_raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
