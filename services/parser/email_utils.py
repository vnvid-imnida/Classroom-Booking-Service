# Uses PEP 8
# Tools: black, flake8, mypy

"""SMTP email delivery for parser notifications (mirrors backend/email_utils)."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

_PLACEHOLDER_MARKERS = (
    "your-email@",
    "your-app-password",
    "YOUR_",
    "changeme",
)


def _email_enabled() -> bool:
    raw = os.getenv("EMAIL_ENABLED", "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _looks_like_placeholder(value: str) -> bool:
    lower = value.lower()
    return any(marker.lower() in lower for marker in _PLACEHOLDER_MARKERS)


class EmailSendError(RuntimeError):
    """Raised when an email cannot be delivered."""


def _smtp_send(host: str, port: int, user: str, password: str, message: EmailMessage) -> None:
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.login(user, password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(user, password)
        smtp.send_message(message)


def send_email(*, to_email: str, subject: str, body: str) -> None:
    """Send a plain-text email via SMTP (or log it when email is disabled)."""
    if not to_email or not str(to_email).strip():
        logger.info("Skip email %r — empty recipient", subject)
        return

    to_email = str(to_email).strip()

    if not _email_enabled():
        msg = f"EMAIL_ENABLED=false — to={to_email} subject={subject!r}\n{body}"
        print(msg, flush=True)
        logger.info(msg)
        return

    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "465"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip().replace(" ", "")
    from_email = os.getenv("SMTP_FROM_EMAIL", user).strip() or user

    if not host or not user or not password or not from_email:
        raise EmailSendError(
            "SMTP не настроен: задайте SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL."
        )
    if _looks_like_placeholder(user) or _looks_like_placeholder(password):
        raise EmailSendError(
            "В .env всё ещё заглушки SMTP. Укажите реальный email и пароль приложения."
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email
    message.set_content(body)

    errors: list[str] = []
    ports_to_try = [port]
    for alt in (465, 587):
        if alt not in ports_to_try:
            ports_to_try.append(alt)

    for try_port in ports_to_try:
        try:
            _smtp_send(host, try_port, user, password, message)
            logger.info("Email sent to %s via %s:%s (%s)", to_email, host, try_port, subject)
            return
        except (smtplib.SMTPException, OSError) as exc:
            err = f"{host}:{try_port} → {exc}"
            errors.append(err)
            logger.warning("SMTP attempt failed: %s", err)

    raise EmailSendError("Не удалось отправить письмо. " + " | ".join(errors))
