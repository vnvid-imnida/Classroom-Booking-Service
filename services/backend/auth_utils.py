# Uses PEP 8
# Tools: black, flake8, mypy

import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "dev-change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "168"))
LINK_TOKEN_TTL_MINUTES = int(os.getenv("LINK_TOKEN_TTL_MINUTES", "30"))
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt.

    Args:
        password: Plaintext password.

    Returns:
        Bcrypt hash string (e.g. ``$2b$12$...``).
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, stored: str) -> bool:
    """Check a plaintext password against a bcrypt hash.

    Args:
        password: Plaintext password to verify.
        stored: Bcrypt hash from ``hash_password``.

    Returns:
        True if the password matches.
    """
    if not stored:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
    except ValueError:
        return False


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
