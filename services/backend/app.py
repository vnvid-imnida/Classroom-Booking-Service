# Uses PEP 8
# Tools: black, flake8, mypy

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(_repo_root / ".env")
except ImportError:
    pass

_services_root = Path(__file__).resolve().parent.parent
if str(_services_root) not in sys.path:
    sys.path.insert(0, str(_services_root))

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Literal

import psycopg2
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from auth.email_domains import role_for_email, validate_spbstu_email
from auth.messages import (
    CAPTCHA_FAILED_RU,
    CAPTCHA_REQUIRED_RU,
    EMAIL_ALREADY_EXISTS_RU,
    EMAIL_NOT_VERIFIED_RU,
    INVALID_VERIFICATION_CODE_RU,
    LOGIN_DB_CONFLICT_RU,
    LOGIN_SERVER_ERROR_RU,
    TELEGRAM_LINKED_OTHER_ACCOUNT_RU,
    VERIFICATION_CODE_SENT_RU,
    WEB_LINKED_OTHER_TELEGRAM_RU,
)
from auth.roles import ROLE_TEACHER, effective_role
from auth_utils import (
    LINK_TOKEN_TTL_MINUTES,
    create_access_token,
    decode_access_token,
    hash_password,
    new_link_token,
    verify_password,
)
from captcha_utils import captcha_enabled, verify_turnstile_token
from db import execute, fetch_all, fetch_one, get_conn
from email_utils import EmailSendError, send_verification_email
from email_verification import issue_verification_code, verify_stored_code

app = FastAPI(title="spbpu-booking-backend", version="1.0.0")
SERVICE_NAME = os.getenv("SERVICE_NAME", "backend")
logger = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    """Build allowed CORS origins from env plus local Vite defaults.

    Returns:
        List of origin URLs for CORSMiddleware.
    """
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    for default in ("http://localhost:5173", "http://127.0.0.1:5173"):
        if default not in origins:
            origins.append(default)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=(
        r"https://.*\.ngrok-free\.app"
        r"|https://.*\.ngrok-free\.dev"
        r"|https://.*\.ngrok\.io"
        r"|https://.*\.ngrok\.app"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _client_ip(request: Request) -> str | None:
    """Extract client IP, honoring X-Forwarded-For when present."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _verify_web_captcha(
    captcha_token: str | None,
    remote_ip: str | None,
    *,
    x_telegram_id: int | None = None,
) -> None:
    """Require Cloudflare Turnstile for browser login/register; skip for Telegram bot."""
    if not captcha_enabled():
        return
    if x_telegram_id is not None:
        return
    if not captcha_token:
        raise HTTPException(400, CAPTCHA_REQUIRED_RU)
    if not verify_turnstile_token(captcha_token, remote_ip):
        raise HTTPException(400, CAPTCHA_FAILED_RU)


def _parse_dt(value: str) -> datetime:
    """Parse ISO datetime string to timezone-aware UTC.

    Args:
        value: ISO-8601 datetime, optionally with ``Z`` suffix.

    Returns:
        Datetime normalized to UTC.
    """
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _user_row_to_dict(row: dict) -> dict:
    """Map a database user row to the public API user shape.

    Args:
        row: User row from PostgreSQL.

    Returns:
        Serialized user dict for API responses.
    """
    return {
        "id": row["id"],
        "telegram_id": row.get("telegram_id"),
        "telegram_username": row.get("telegram_username"),
        "email": row.get("email"),
        "full_name": row["full_name"],
        "role": effective_role(row),
        "is_active": row["is_active"],
    }


def get_current_user(
    x_telegram_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    authorization: str | None = Header(default=None),
) -> dict:
    """Resolve the authenticated user from Telegram id or Bearer JWT.

    Args:
        x_telegram_id: Telegram user id header (bot clients).
        authorization: Optional ``Bearer`` JWT (web clients).

    Returns:
        Active user profile dict.

    Raises:
        HTTPException: 401/404 when authentication fails or Telegram is unlinked.
    """
    with get_conn() as conn:
        if x_telegram_id is not None:
            user = fetch_one(
                conn,
                """
                SELECT id::text, telegram_id, telegram_username, email, full_name, role, is_active
                FROM users WHERE telegram_id = %s AND is_active = true
                """,
                (x_telegram_id,),
            )
            if user:
                return _user_row_to_dict(user)
            raise HTTPException(
                404,
                "Telegram not linked. Register on the web app and use /start link_<token>.",
            )

        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
            user_id = decode_access_token(token)
            if user_id:
                user = fetch_one(
                    conn,
                    """
                    SELECT id::text, telegram_id, telegram_username, email, full_name, role, is_active
                    FROM users WHERE id = %s::uuid AND is_active = true
                    """,
                    (user_id,),
                )
                if user:
                    return _user_row_to_dict(user)

    raise HTTPException(401, "Authentication required (X-Telegram-Id or Bearer token)")


class RegisterBody(BaseModel):
    telegram_id: int
    telegram_username: str | None = None
    full_name: str


class WebRegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    captcha_token: str | None = None


class WebLoginBody(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailBody(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class LinkTelegramBody(BaseModel):
    token: str = Field(min_length=8, max_length=128)


class BookingRequestCreate(BaseModel):
    room_id: int
    purpose_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    starts_at: str
    ends_at: str
    action: Literal["CREATE", "RESCHEDULE"] = "CREATE"
    target_booking_id: str | None = None


class RejectBody(BaseModel):
    comment: str | None = None



@app.get("/")
def root():
    """Service index with links to docs and health."""
    return {
        "service": SERVICE_NAME,
        "docs": "/docs",
        "health": "/health",
        "web_login": "http://localhost:5173/login",
    }


@app.get("/health")
def health():
    """Liveness probe for orchestration."""
    return {"status": "healthy", "service": SERVICE_NAME}


@app.post("/api/v1/users/register")
def register_user(body: RegisterBody):
    """Legacy Telegram-only upsert (prefer web register + link flow).

    Args:
        body: Telegram id, optional username, and display name.

    Returns:
        Upserted user record.

    Raises:
        HTTPException: On database errors (via connection layer).
    """
    username = body.telegram_username or f"tg_{body.telegram_id}"
    if not username.startswith("@"):
        username = f"@{username.lstrip('@')}"

    with get_conn() as conn:
        execute(
            conn,
            """
            INSERT INTO users (telegram_id, telegram_username, full_name, role, is_active)
            VALUES (%s, %s, %s, %s, true)
            ON CONFLICT (telegram_id) DO UPDATE
            SET telegram_username = EXCLUDED.telegram_username,
                full_name = EXCLUDED.full_name,
                is_active = true
            """,
            (body.telegram_id, username, body.full_name, ROLE_TEACHER),
        )
        user = fetch_one(
            conn,
            """
            SELECT id::text, telegram_id, telegram_username, email, full_name, role
            FROM users WHERE telegram_id = %s
            """,
            (body.telegram_id,),
        )
    return user


@app.post("/api/v1/auth/register")
def web_register(
    body: WebRegisterBody,
    request: Request,
    x_telegram_id: int | None = Header(default=None, alias="X-Telegram-Id"),
):
    """Register a web user with email and password.

    Returns **202** and emails a verification code (no JWT until verified).
    ``X-Telegram-Id`` only skips captcha — email verification is still required.

    Args:
        body: Email, password, and full name.
        request: HTTP request (client IP for Turnstile).
        x_telegram_id: When set (Telegram bot), captcha is not required.

    Returns:
        202 with verification instructions.

    Raises:
        HTTPException: 400 for invalid domain or captcha; 409 if email is already registered.
    """
    _verify_web_captcha(
        body.captcha_token, _client_ip(request), x_telegram_id=x_telegram_id
    )
    email = body.email.strip().lower()
    ok, domain_err = validate_spbstu_email(email)
    if not ok:
        raise HTTPException(400, domain_err or "Invalid email domain")

    with get_conn() as conn:
        existing = fetch_one(
            conn,
            """
            SELECT id::text, email_verified
            FROM users WHERE lower(email) = %s
            """,
            (email,),
        )
        if existing:
            if existing.get("email_verified"):
                raise HTTPException(409, EMAIL_ALREADY_EXISTS_RU)
            code = issue_verification_code(conn, existing["id"])
            try:
                send_verification_email(
                    to_email=email, code=code, full_name=body.full_name
                )
            except EmailSendError as exc:
                raise HTTPException(503, str(exc)) from exc
            return JSONResponse(
                status_code=202,
                content={
                    "message": VERIFICATION_CODE_SENT_RU,
                    "email": email,
                    "verification_required": True,
                },
            )

        user_role = role_for_email(email)
        user = fetch_one(
            conn,
            """
            INSERT INTO users (email, password_hash, full_name, role, is_active, email_verified)
            VALUES (%s, %s, %s, %s, true, false)
            RETURNING id::text, email, full_name, role, telegram_id
            """,
            (
                email,
                hash_password(body.password),
                body.full_name,
                user_role,
            ),
        )

        code = issue_verification_code(conn, user["id"])
        try:
            send_verification_email(to_email=email, code=code, full_name=body.full_name)
        except EmailSendError as exc:
            raise HTTPException(503, str(exc)) from exc

    return JSONResponse(
        status_code=202,
        content={
            "message": VERIFICATION_CODE_SENT_RU,
            "email": email,
            "verification_required": True,
        },
    )


@app.post("/api/v1/auth/verify-email")
def verify_email(body: VerifyEmailBody):
    """Confirm email with a 6-digit code and issue JWT.

    Args:
        body: Registered email and verification code.

    Returns:
        JWT access token and user profile.

    Raises:
        HTTPException: 400 for invalid code; 404 if user not found.
    """
    email = body.email.strip().lower()
    ok, domain_err = validate_spbstu_email(email)
    if not ok:
        raise HTTPException(400, domain_err or "Invalid email domain")

    with get_conn() as conn:
        user = fetch_one(
            conn,
            """
            SELECT id::text, email, full_name, role, telegram_id, email_verified
            FROM users WHERE lower(email) = %s AND is_active = true
            """,
            (email,),
        )
        if not user:
            raise HTTPException(404, "Пользователь с таким email не найден")
        if user.get("email_verified"):
            token = create_access_token(user["id"])
            return {"access_token": token, "token_type": "bearer", "user": user}

        valid, err = verify_stored_code(conn, user["id"], body.code)
        if not valid:
            raise HTTPException(400, err or INVALID_VERIFICATION_CODE_RU)

        user["email_verified"] = True

    token = create_access_token(user["id"])
    return {"access_token": token, "token_type": "bearer", "user": user}


def _telegram_username_header(x_telegram_username: str | None, x_telegram_id: int) -> str:
    """Normalize Telegram username for storage (leading ``@``).

    Args:
        x_telegram_username: Username from header, if any.
        x_telegram_id: Fallback id when username is missing.

    Returns:
        Username string with ``@`` prefix.
    """
    username = x_telegram_username or f"tg_{x_telegram_id}"
    if not username.startswith("@"):
        username = f"@{username.lstrip('@')}"
    return username


def _is_legacy_telegram_only_user(row: dict) -> bool:
    """Return True for bot-only users from the legacy register flow.

    Args:
        row: User row with optional email field.

    Returns:
        True when the user has no web email on file.
    """
    email = row.get("email")
    return not email or not str(email).strip()


def _release_telegram_from_other_user(
    conn,
    *,
    x_telegram_id: int,
    target_user_id: str,
) -> bool:
    """Release telegram_id from another user or reject if already linked.

    Args:
        conn: Open database connection.
        x_telegram_id: Telegram id to bind.
        target_user_id: Web user id receiving the link.

    Returns:
        True when a legacy-only holder was cleared for reassignment.

    Raises:
        HTTPException: 409 when Telegram is linked to another web account.
    """
    other = fetch_one(
        conn,
        """
        SELECT id::text, email FROM users
        WHERE telegram_id = %s AND is_active = true AND id != %s::uuid
        """,
        (x_telegram_id, target_user_id),
    )
    if not other:
        return False
    if _is_legacy_telegram_only_user(other):
        execute(
            conn,
            """
            UPDATE users
            SET telegram_id = NULL, telegram_username = NULL
            WHERE id = %s::uuid
            """,
            (other["id"],),
        )
        return True
    raise HTTPException(409, TELEGRAM_LINKED_OTHER_ACCOUNT_RU)


def _release_username_from_other_user(
    conn,
    *,
    username: str,
    target_user_id: str,
) -> None:
    """Clear duplicate ``telegram_username`` on other rows before binding.

    Raises:
        HTTPException: 409 when another web account already uses this username.
    """
    other = fetch_one(
        conn,
        """
        SELECT id::text, email FROM users
        WHERE telegram_username = %s AND is_active = true AND id != %s::uuid
        """,
        (username, target_user_id),
    )
    if not other:
        return
    if _is_legacy_telegram_only_user(other):
        execute(
            conn,
            """
            UPDATE users
            SET telegram_username = NULL
            WHERE id = %s::uuid
            """,
            (other["id"],),
        )
        return
    raise HTTPException(409, TELEGRAM_LINKED_OTHER_ACCOUNT_RU)


_LEGACY_TELEGRAM_REASSIGNED_NOTE = (
    "Telegram was moved from a legacy bot-only account to your web profile. "
    "Run migration 005+ if you still have orphan rows in the database."
)


def _bind_telegram_to_web_user(
    conn,
    *,
    user_id: str,
    x_telegram_id: int,
    username: str,
) -> tuple[dict, str | None]:
    """Attach Telegram credentials to an existing web user.

    Args:
        conn: Open database connection.
        user_id: Target web user UUID.
        x_telegram_id: Telegram user id.
        username: Normalized Telegram username.

    Returns:
        Tuple of updated user dict and optional migration note.

    Raises:
        HTTPException: 401/409 on missing user or conflicting links.
    """
    legacy_reassigned = _release_telegram_from_other_user(
        conn, x_telegram_id=x_telegram_id, target_user_id=user_id
    )
    _release_username_from_other_user(
        conn, username=username, target_user_id=user_id
    )

    user = fetch_one(
        conn,
        """
        SELECT id::text, telegram_id, email, full_name, role, is_active
        FROM users WHERE id = %s::uuid
        """,
        (user_id,),
    )
    if not user or not user.get("is_active"):
        raise HTTPException(401, "User not found")

    existing_tg = user.get("telegram_id")
    if existing_tg and int(existing_tg) != x_telegram_id:
        raise HTTPException(409, WEB_LINKED_OTHER_TELEGRAM_RU)

    execute(
        conn,
        """
        UPDATE users
        SET telegram_id = %s,
            telegram_username = %s,
            is_active = true
        WHERE id = %s::uuid
        """,
        (x_telegram_id, username, user_id),
    )
    updated = fetch_one(
        conn,
        """
        SELECT id::text, telegram_id, telegram_username, email, full_name, role
        FROM users WHERE id = %s::uuid
        """,
        (user_id,),
    )
    note = _LEGACY_TELEGRAM_REASSIGNED_NOTE if legacy_reassigned else None
    return updated, note


@app.get("/api/v1/auth/check-email")
def check_email_exists(email: EmailStr = Query(...)):
    """Return whether a web account exists for the given email (bot login pre-check).

    Args:
        email: Email address to look up (case-insensitive).

    Returns:
        Dict with ``exists`` boolean.
    """
    normalized = str(email).strip().lower()
    ok, domain_err = validate_spbstu_email(normalized)
    if not ok:
        raise HTTPException(400, domain_err or "Invalid email domain")
    with get_conn() as conn:
        row = fetch_one(
            conn,
            """
            SELECT id::text, email_verified
            FROM users WHERE lower(email) = %s AND is_active = true
            """,
            (normalized,),
        )
    if not row:
        return {"exists": False, "email_verified": False}
    return {
        "exists": True,
        "email_verified": bool(row.get("email_verified")),
    }


@app.post("/api/v1/auth/login")
def web_login(
    body: WebLoginBody,
    request: Request,
    x_telegram_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    x_telegram_username: str | None = Header(default=None, alias="X-Telegram-Username"),
):
    """Authenticate with email/password; optionally bind Telegram in the same request.

    Args:
        body: Login credentials.
        request: HTTP request (client IP for Turnstile).
        x_telegram_id: Optional Telegram id to link on successful login.
        x_telegram_username: Optional Telegram username header.

    Returns:
        JWT access token and user profile.

    Raises:
        HTTPException: 400 for invalid email domain; 401/403/404 for credentials; 409 on link conflicts.
    """
    email = body.email.strip().lower()
    ok, domain_err = validate_spbstu_email(email)
    if not ok:
        raise HTTPException(400, domain_err or "Invalid email domain")
    try:
        with get_conn() as conn:
            user = fetch_one(
                conn,
                """
                SELECT id::text, email, password_hash, full_name, role, telegram_id,
                       is_active, email_verified
                FROM users WHERE lower(email) = %s
                """,
                (email,),
            )
            if not user or not user.get("is_active"):
                raise HTTPException(404, "Пользователь с таким email не найден")
            if not user.get("password_hash"):
                raise HTTPException(404, "Пользователь с таким email не найден")
            if not verify_password(body.password, user["password_hash"]):
                raise HTTPException(401, "Неверный пароль")
            if not user.get("email_verified", True):
                raise HTTPException(403, EMAIL_NOT_VERIFIED_RU)

            expected_role = effective_role(user)
            if user.get("role") != expected_role:
                execute(
                    conn,
                    "UPDATE users SET role = %s WHERE id = %s::uuid",
                    (expected_role, user["id"]),
                )
                user["role"] = expected_role

            # Commit role updates before Telegram bind. A 409 on bind used to
            # raise HTTPException and roll back the whole transaction.
            conn.commit()

            if x_telegram_id is not None:
                user, _ = _bind_telegram_to_web_user(
                    conn,
                    user_id=user["id"],
                    x_telegram_id=x_telegram_id,
                    username=_telegram_username_header(
                        x_telegram_username, x_telegram_id
                    ),
                )
    except HTTPException:
        raise
    except psycopg2.IntegrityError as exc:
        logger.warning("login integrity error: %s", exc)
        raise HTTPException(409, LOGIN_DB_CONFLICT_RU) from exc
    except psycopg2.Error as exc:
        logger.exception("login database error")
        err = str(exc).lower()
        if "users_role_check" in err or "student" in err:
            raise HTTPException(
                500,
                "Ошибка БД: примените миграцию database/migrations/008_add_student_role.sql",
            ) from exc
        if "password_hash" in err or ("column" in err and "email" in err):
            raise HTTPException(
                500,
                "Ошибка БД: примените миграцию database/migrations/005_user_auth_telegram_link.sql",
            ) from exc
        raise HTTPException(500, LOGIN_SERVER_ERROR_RU) from exc

    token = create_access_token(user["id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": effective_role(user),
            "telegram_id": user.get("telegram_id"),
        },
    }


@app.post("/api/v1/auth/link-token")
def create_link_token(user: dict = Depends(get_current_user)):
    """Create a one-time token for linking Telegram via ``/start link_<token>``.

    Args:
        user: Authenticated web user (JWT).

    Returns:
        Token, expiry, and bot command hint.

    Raises:
        HTTPException: 409 if Telegram is already linked.
    """
    if user.get("telegram_id"):
        raise HTTPException(409, "Telegram account already linked")

    token = new_link_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=LINK_TOKEN_TTL_MINUTES)
    with get_conn() as conn:
        execute(
            conn,
            "DELETE FROM telegram_link_tokens WHERE user_id = %s::uuid",
            (user["id"],),
        )
        execute(
            conn,
            """
            INSERT INTO telegram_link_tokens (token, user_id, expires_at)
            VALUES (%s, %s::uuid, %s)
            """,
            (token, user["id"], expires_at),
        )
    return {
        "token": token,
        "expires_at": expires_at.isoformat(),
        "bot_command": f"/start link_{token}",
        "expires_in_minutes": LINK_TOKEN_TTL_MINUTES,
    }


@app.post("/api/v1/users/link-telegram")
def link_telegram(
    body: LinkTelegramBody,
    x_telegram_id: int = Header(alias="X-Telegram-Id"),
    x_telegram_username: str | None = Header(default=None, alias="X-Telegram-Username"),
):
    """Consume a link token and bind Telegram to the associated web user.

    Args:
        body: One-time link token from the web app.
        x_telegram_id: Telegram user id header.
        x_telegram_username: Optional Telegram username header.

    Returns:
        Updated user profile, optionally with a migration note.

    Raises:
        HTTPException: 404/410 for invalid or expired tokens; 409 if already linked.
    """
    username = x_telegram_username or f"tg_{x_telegram_id}"
    if not username.startswith("@"):
        username = f"@{username.lstrip('@')}"

    with get_conn() as conn:
        row = fetch_one(
            conn,
            """
            SELECT t.user_id::text, t.expires_at, u.telegram_id
            FROM telegram_link_tokens t
            JOIN users u ON u.id = t.user_id
            WHERE t.token = %s
            """,
            (body.token,),
        )
        if not row:
            raise HTTPException(404, "Invalid or expired link token")
        if row["expires_at"] < datetime.now(timezone.utc):
            execute(conn, "DELETE FROM telegram_link_tokens WHERE token = %s", (body.token,))
            raise HTTPException(410, "Link token expired. Generate a new one on the web app.")

        if row.get("telegram_id"):
            raise HTTPException(409, "Web account already has Telegram linked")

        user, migration_note = _bind_telegram_to_web_user(
            conn,
            user_id=row["user_id"],
            x_telegram_id=x_telegram_id,
            username=username,
        )
        execute(conn, "DELETE FROM telegram_link_tokens WHERE token = %s", (body.token,))

    if migration_note:
        return {"user": user, "migration_note": migration_note}
    return user


@app.post("/api/v1/auth/telegram-logout")
def telegram_logout(x_telegram_id: int = Header(alias="X-Telegram-Id")):
    """Unlink Telegram from the web account (bot ``/logout`` and ``/login``).

    Args:
        x_telegram_id: Telegram user id to unlink.

    Returns:
        ``{"ok": true}`` on success.

    Raises:
        HTTPException: 404 when Telegram is not linked.
    """
    with get_conn() as conn:
        user = fetch_one(
            conn,
            """
            SELECT id::text FROM users
            WHERE telegram_id = %s AND is_active = true
            """,
            (x_telegram_id,),
        )
        if not user:
            raise HTTPException(404, "Telegram not linked")
        execute(
            conn,
            """
            UPDATE users
            SET telegram_id = NULL, telegram_username = NULL
            WHERE id = %s::uuid
            """,
            (user["id"],),
        )
    return {"ok": True}


@app.get("/api/v1/me")
def me(user: dict = Depends(get_current_user)):
    """Return the authenticated user profile."""
    return user


@app.get("/api/v1/buildings")
def list_buildings(user: dict = Depends(get_current_user)):
    """List all campus buildings."""
    with get_conn() as conn:
        return fetch_all(
            conn,
            "SELECT id, code, name, address FROM buildings ORDER BY code",
        )


@app.get("/api/v1/rooms")
def list_rooms(
    user: dict = Depends(get_current_user),
    building_code: str | None = None,
    min_capacity: int | None = None,
    has_projector: bool | None = None,
    has_whiteboard: bool | None = None,
    is_accessible: bool | None = None,
):
    """Search active rooms with optional building and amenity filters."""
    clauses = ["r.is_active = true"]
    params: list = []
    if building_code:
        clauses.append("b.code = %s")
        params.append(building_code)
    if min_capacity is not None:
        clauses.append("r.capacity >= %s")
        params.append(min_capacity)
    if has_projector is not None:
        clauses.append("r.has_projector = %s")
        params.append(has_projector)
    if has_whiteboard is not None:
        clauses.append("r.has_whiteboard = %s")
        params.append(has_whiteboard)
    if is_accessible is not None:
        clauses.append("r.is_accessible = %s")
        params.append(is_accessible)

    where = " AND ".join(clauses)
    with get_conn() as conn:
        return fetch_all(
            conn,
            f"""
            SELECT r.id, b.code AS building_code, b.name AS building_name,
                   r.room_number, r.floor, r.capacity,
                   r.has_projector, r.has_whiteboard, r.is_accessible
            FROM rooms r
            JOIN buildings b ON b.id = r.building_id
            WHERE {where}
            ORDER BY b.code, r.room_number
            """,
            tuple(params),
        )


@app.get("/api/v1/rooms/available")
def available_rooms(
    user: dict = Depends(get_current_user),
    starts_at: str = Query(...),
    ends_at: str = Query(...),
    building_code: str | None = None,
):
    """List rooms free for the given time interval.

    Args:
        starts_at: Interval start (ISO-8601).
        ends_at: Interval end (ISO-8601).
        building_code: Optional building filter.

    Raises:
        HTTPException: 400 when ``ends_at`` is not after ``starts_at``.
    """
    start_dt = _parse_dt(starts_at)
    end_dt = _parse_dt(ends_at)
    if end_dt <= start_dt:
        raise HTTPException(400, "ends_at must be after starts_at")

    clauses = ["r.is_active = true"]
    params: list = []
    if building_code:
        clauses.append("b.code = %s")
        params.append(building_code)
    params.extend([start_dt, end_dt])
    where = " AND ".join(clauses)

    with get_conn() as conn:
        return fetch_all(
            conn,
            f"""
            SELECT r.id, b.code AS building_code, b.name AS building_name,
                   r.room_number, r.floor, r.capacity
            FROM rooms r
            JOIN buildings b ON b.id = r.building_id
            WHERE {where}
              AND NOT EXISTS (
                  SELECT 1 FROM bookings bk
                  WHERE bk.room_id = r.id
                    AND bk.status = 'ACTIVE'
                    AND tstzrange(bk.starts_at, bk.ends_at, '[)') &&
                        tstzrange(%s, %s, '[)')
              )
            ORDER BY b.code, r.room_number
            """,
            tuple(params),
        )


@app.get("/api/v1/event-purposes")
def event_purposes(user: dict = Depends(get_current_user)):
    """List active event purpose codes for booking requests."""
    with get_conn() as conn:
        return fetch_all(
            conn,
            "SELECT id, code, name FROM event_purposes WHERE is_active = true ORDER BY id",
        )


@app.get("/api/v1/rooms/{room_id}/occupancy")
def room_occupancy(
    room_id: int,
    user: dict = Depends(get_current_user),
    date: str = Query(..., description="YYYY-MM-DD"),
):
    """Return bookings and pending requests overlapping a room on one day.

    Args:
        room_id: Room primary key.
        date: Calendar day in ``YYYY-MM-DD`` format.
    """
    day_start = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    with get_conn() as conn:
        return fetch_all(
            conn,
            """
            SELECT id::text, room_id, title, source, status,
                   starts_at, ends_at
            FROM (
                SELECT b.id, b.room_id, b.title, 'booking' AS source, b.status::text,
                       b.starts_at, b.ends_at
                FROM bookings b
                WHERE b.status = 'ACTIVE'
                UNION ALL
                SELECT br.id, br.room_id, br.title, 'pending_request' AS source,
                       br.status::text, br.starts_at, br.ends_at
                FROM booking_requests br
                WHERE br.status = 'PENDING'
            ) occupancy
            WHERE room_id = %s
              AND starts_at < %s
              AND ends_at > %s
            ORDER BY starts_at
            """,
            (room_id, day_end, day_start),
        )


@app.post("/api/v1/booking-requests")
def create_request(body: BookingRequestCreate, user: dict = Depends(get_current_user)):
    """Create a draft booking request after availability check.

    Raises:
        HTTPException: 400/409 for invalid times or occupied room.
    """
    start_dt = _parse_dt(body.starts_at)
    end_dt = _parse_dt(body.ends_at)
    if end_dt <= start_dt:
        raise HTTPException(400, "ends_at must be after starts_at")
    if body.action == "RESCHEDULE" and not body.target_booking_id:
        raise HTTPException(400, "target_booking_id required for RESCHEDULE")

    with get_conn() as conn:
        available = fetch_all(
            conn,
            """
            SELECT r.id FROM rooms r
            WHERE r.id = %s AND r.is_active = true
              AND NOT EXISTS (
                  SELECT 1 FROM bookings bk
                  WHERE bk.room_id = r.id AND bk.status = 'ACTIVE'
                    AND tstzrange(bk.starts_at, bk.ends_at, '[)') &&
                        tstzrange(%s, %s, '[)')
              )
            """,
            (body.room_id, start_dt, end_dt),
        )
        if not available:
            raise HTTPException(409, "Room is not available for the selected time slot")

        row = fetch_one(
            conn,
            """
            INSERT INTO booking_requests (
                requester_id, action, target_booking_id, room_id, purpose_id,
                title, description, starts_at, ends_at, status
            )
            VALUES (%s::uuid, %s, %s::uuid, %s, %s, %s, %s, %s, %s, 'DRAFT')
            RETURNING id::text, status, room_id, purpose_id, title, starts_at, ends_at, action
            """,
            (
                user["id"],
                body.action,
                body.target_booking_id,
                body.room_id,
                body.purpose_id,
                body.title,
                body.description,
                start_dt,
                end_dt,
            ),
        )
    return row


@app.post("/api/v1/booking-requests/{request_id}/submit")
def submit_request(request_id: str, user: dict = Depends(get_current_user)):
    """Submit a draft request for moderator review.

    Raises:
        HTTPException: 404 if not found; 409 if status is not DRAFT.
    """
    with get_conn() as conn:
        req = fetch_one(
            conn,
            """
            SELECT id::text, requester_id::text, status
            FROM booking_requests WHERE id = %s::uuid
            """,
            (request_id,),
        )
        if not req or req["requester_id"] != user["id"]:
            raise HTTPException(404, "Request not found")
        if req["status"] != "DRAFT":
            raise HTTPException(409, f"Cannot submit request in status {req['status']}")

        execute(
            conn,
            """
            UPDATE booking_requests
            SET status = 'PENDING', submitted_at = now(), updated_at = now()
            WHERE id = %s::uuid
            """,
            (request_id,),
        )
        return fetch_one(
            conn,
            """
            SELECT id::text, status, submitted_at, room_id, starts_at, ends_at, title
            FROM booking_requests WHERE id = %s::uuid
            """,
            (request_id,),
        )


@app.post("/api/v1/booking-requests/{request_id}/cancel")
def cancel_request(request_id: str, user: dict = Depends(get_current_user)):
    """Cancel own draft or pending booking request.

    Raises:
        HTTPException: 404/409 when cancel is not allowed.
    """
    with get_conn() as conn:
        req = fetch_one(
            conn,
            """
            SELECT id::text, requester_id::text, status
            FROM booking_requests WHERE id = %s::uuid
            """,
            (request_id,),
        )
        if not req or req["requester_id"] != user["id"]:
            raise HTTPException(404, "Request not found")
        if req["status"] not in ("DRAFT", "PENDING"):
            raise HTTPException(
                409,
                f"Only draft or pending requests can be cancelled (current: {req['status']})",
            )

        execute(
            conn,
            """
            UPDATE booking_requests
            SET status = 'CANCELLED', updated_at = now()
            WHERE id = %s::uuid
            """,
            (request_id,),
        )
        return {"id": request_id, "status": "CANCELLED"}


@app.get("/api/v1/booking-requests/me")
def my_requests(
    user: dict = Depends(get_current_user),
    scope: Literal["active", "archive"] = "active",
):
    """List the current user's booking requests (active or archive)."""
    if scope == "active":
        status_filter = "br.status IN ('DRAFT', 'PENDING')"
    else:
        status_filter = "br.status IN ('CANCELLED', 'REJECTED', 'APPROVED')"

    with get_conn() as conn:
        return fetch_all(
            conn,
            f"""
            SELECT br.id::text, br.status, br.title, br.starts_at, br.ends_at,
                   b.code AS building_code, r.room_number, ep.name AS purpose_name
            FROM booking_requests br
            JOIN rooms r ON r.id = br.room_id
            JOIN buildings b ON b.id = r.building_id
            JOIN event_purposes ep ON ep.id = br.purpose_id
            WHERE br.requester_id = %s::uuid AND {status_filter}
            ORDER BY br.created_at DESC
            LIMIT 20
            """,
            (user["id"],),
        )


@app.get("/api/v1/bookings/me")
def my_bookings(
    user: dict = Depends(get_current_user),
    scope: Literal["active", "archive"] = "active",
):
    """List the current user's confirmed bookings (active or archive)."""
    if scope == "active":
        condition = """
            b.organizer_id = %s::uuid AND b.source = 'MANUAL'
            AND b.status = 'ACTIVE' AND b.ends_at >= now()
        """
    else:
        condition = """
            b.organizer_id = %s::uuid AND b.source = 'MANUAL'
            AND (b.status IN ('CANCELLED', 'RESCHEDULED', 'COMPLETED') OR b.ends_at < now())
        """

    with get_conn() as conn:
        return fetch_all(
            conn,
            f"""
            SELECT b.id::text, b.status, b.title, b.starts_at, b.ends_at,
                   bd.code AS building_code, r.room_number
            FROM bookings b
            JOIN rooms r ON r.id = b.room_id
            JOIN buildings bd ON bd.id = r.building_id
            WHERE {condition}
            ORDER BY b.starts_at DESC
            LIMIT 20
            """,
            (user["id"],),
        )


@app.post("/api/v1/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: str, user: dict = Depends(get_current_user)):
    """Cancel an active booking more than 24 hours before start.

    Raises:
        HTTPException: 404/409 when cancel is not allowed.
    """
    with get_conn() as conn:
        booking = fetch_one(
            conn,
            """
            SELECT id::text, organizer_id::text, status, starts_at
            FROM bookings WHERE id = %s::uuid
            """,
            (booking_id,),
        )
        if not booking or booking["organizer_id"] != user["id"]:
            raise HTTPException(404, "Booking not found")
        if booking["status"] != "ACTIVE":
            raise HTTPException(409, "Only active bookings can be cancelled")

        starts_at = booking["starts_at"]
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)
        if starts_at - datetime.now(timezone.utc) < timedelta(hours=24):
            raise HTTPException(409, "Cancellation is allowed only more than 24 hours before start")

        execute(
            conn,
            """
            UPDATE bookings
            SET status = 'CANCELLED', cancelled_by = %s::uuid,
                cancelled_at = now(), cancel_reason = 'Cancelled by teacher via Telegram'
            WHERE id = %s::uuid
            """,
            (user["id"], booking_id),
        )
        return {"id": booking_id, "status": "CANCELLED"}


def _require_moderator(user: dict) -> None:
    """Ensure the user has moderator or admin role.

    Raises:
        HTTPException: 403 when role is insufficient.
    """
    if user["role"] not in ("MODERATOR", "ADMIN"):
        raise HTTPException(403, "Moderator role required")


@app.get("/api/v1/moderation/requests")
def moderation_queue(
    user: dict = Depends(get_current_user),
    scope: Literal["queue", "all"] = Query(
        "queue",
        description="queue = PENDING only; all = submitted requests for admin panel",
    ),
):
    """List booking requests for moderators (pending queue or full history)."""
    _require_moderator(user)
    if scope == "all":
        status_filter = "br.status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')"
        order_by = "br.submitted_at DESC NULLS LAST, br.created_at DESC"
    else:
        status_filter = "br.status = 'PENDING'"
        order_by = "br.submitted_at ASC"

    with get_conn() as conn:
        return fetch_all(
            conn,
            f"""
            SELECT br.id::text, br.title, br.starts_at, br.ends_at, br.status,
                   u.full_name AS requester_name, u.email AS requester_email,
                   u.telegram_username,
                   b.code AS building_code, r.room_number,
                   ep.code AS purpose_code, ep.name AS purpose_name
            FROM booking_requests br
            JOIN users u ON u.id = br.requester_id
            JOIN rooms r ON r.id = br.room_id
            JOIN buildings b ON b.id = r.building_id
            JOIN event_purposes ep ON ep.id = br.purpose_id
            WHERE {status_filter}
            ORDER BY {order_by}
            LIMIT 100
            """,
        )


@app.post("/api/v1/moderation/requests/{request_id}/approve")
def approve_request(request_id: str, user: dict = Depends(get_current_user)):
    """Approve a pending request and create an active booking.

    Raises:
        HTTPException: 404/409 when approval is not allowed.
    """
    _require_moderator(user)
    with get_conn() as conn:
        req = fetch_one(
            conn,
            """
            SELECT id::text, requester_id::text, room_id, purpose_id, title, description,
                   starts_at, ends_at, status
            FROM booking_requests WHERE id = %s::uuid
            """,
            (request_id,),
        )
        if not req:
            raise HTTPException(404, "Request not found")
        if req["status"] != "PENDING":
            raise HTTPException(409, f"Cannot approve request in status {req['status']}")

        booking = fetch_one(
            conn,
            """
            INSERT INTO bookings (
                request_id, organizer_id, room_id, purpose_id, title, description,
                starts_at, ends_at, source, status
            )
            VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s, 'MANUAL', 'ACTIVE')
            RETURNING id::text, status, starts_at, ends_at
            """,
            (
                request_id,
                req["requester_id"],
                req["room_id"],
                req["purpose_id"],
                req["title"],
                req["description"],
                req["starts_at"],
                req["ends_at"],
            ),
        )

        execute(
            conn,
            """
            UPDATE booking_requests
            SET status = 'APPROVED', moderated_by = %s::uuid,
                moderated_at = now(), updated_at = now()
            WHERE id = %s::uuid
            """,
            (user["id"], request_id),
        )
        return {"request_id": request_id, "booking": booking}


@app.post("/api/v1/moderation/requests/{request_id}/reject")
def reject_request(request_id: str, body: RejectBody, user: dict = Depends(get_current_user)):
    """Reject a pending request with an optional moderator comment.

    Raises:
        HTTPException: 404/409 when rejection is not allowed.
    """
    _require_moderator(user)
    with get_conn() as conn:
        req = fetch_one(
            conn,
            "SELECT id::text, status FROM booking_requests WHERE id = %s::uuid",
            (request_id,),
        )
        if not req:
            raise HTTPException(404, "Request not found")
        if req["status"] != "PENDING":
            raise HTTPException(409, f"Cannot reject request in status {req['status']}")

        execute(
            conn,
            """
            UPDATE booking_requests
            SET status = 'REJECTED', moderated_by = %s::uuid, moderated_at = now(),
                moderation_comment = %s, updated_at = now()
            WHERE id = %s::uuid
            """,
            (user["id"], body.comment, request_id),
        )
        return {"request_id": request_id, "status": "REJECTED"}
