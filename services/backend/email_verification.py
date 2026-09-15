# Uses PEP 8
# Tools: black, flake8, mypy

"""Email verification codes: issue, verify, and persist."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from auth_utils import hash_password, verify_password
from db import execute, fetch_one

logger = logging.getLogger(__name__)

CODE_TTL_MINUTES = 15
MAX_VERIFY_ATTEMPTS = 5


def generate_verification_code() -> str:
    """Return a 6-digit numeric code."""
    return f"{secrets.randbelow(900_000) + 100_000:06d}"


def issue_verification_code(conn, user_id: str) -> str:
    """Invalidate prior codes and store a new hashed code for the user."""
    execute(
        conn,
        "DELETE FROM email_verification_codes WHERE user_id = %s::uuid",
        (user_id,),
    )
    code = generate_verification_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=CODE_TTL_MINUTES)
    execute(
        conn,
        """
        INSERT INTO email_verification_codes (user_id, code_hash, expires_at)
        VALUES (%s::uuid, %s, %s)
        """,
        (user_id, hash_password(code), expires_at),
    )
    return code


def verify_stored_code(conn, user_id: str, code: str) -> tuple[bool, str | None]:
    """Check the submitted code against the latest non-expired record.

    Returns:
        (True, None) on success; (False, error_message) on failure.
    """
    row = fetch_one(
        conn,
        """
        SELECT id::text, code_hash, expires_at, attempts
        FROM email_verification_codes
        WHERE user_id = %s::uuid
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,),
    )
    if not row:
        return False, "Код не найден. Зарегистрируйтесь снова."

    if row["attempts"] >= MAX_VERIFY_ATTEMPTS:
        return False, "Превышено число попыток. Зарегистрируйтесь снова."

    now = datetime.now(timezone.utc)
    expires_at = row["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        return False, "Срок действия кода истёк. Зарегистрируйтесь снова."

    if not verify_password(code, row["code_hash"]):
        execute(
            conn,
            """
            UPDATE email_verification_codes
            SET attempts = attempts + 1
            WHERE id = %s::uuid
            """,
            (row["id"],),
        )
        remaining = MAX_VERIFY_ATTEMPTS - row["attempts"] - 1
        if remaining <= 0:
            return False, "Неверный код. Превышено число попыток."
        return False, f"Неверный код. Осталось попыток: {remaining}."

    execute(
        conn,
        "DELETE FROM email_verification_codes WHERE user_id = %s::uuid",
        (user_id,),
    )
    execute(
        conn,
        "UPDATE users SET email_verified = true WHERE id = %s::uuid",
        (user_id,),
    )
    logger.info("Email verified for user %s", user_id)
    return True, None
