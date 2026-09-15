# Uses PEP 8
# Tools: black, flake8, mypy

"""SMTP email delivery for auth flows."""

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
    """Raised when a verification email cannot be delivered."""


def _smtp_send(host: str, port: int, user: str, password: str, message: EmailMessage) -> None:
    """Send via SMTP_SSL (465) or STARTTLS (587)."""
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


def send_verification_email(*, to_email: str, code: str, full_name: str) -> None:
    """Send a 6-digit verification code via SMTP (or log it when email is disabled)."""
    subject = "Код подтверждения — SPbPU Booking"
    body = (
        f"Здравствуйте, {full_name}!\n\n"
        f"Ваш код подтверждения email: {code}\n\n"
        "Код действует 15 минут. Если вы не регистрировались — проигнорируйте письмо."
    )

    if not _email_enabled():
        msg = f"EMAIL_ENABLED=false — verification code for {to_email}: {code}"
        print(msg, flush=True)
        logger.info(msg)
        return

    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "465"))
    user = os.getenv("SMTP_USER", "").strip()
    # Gmail app passwords are often copied with spaces
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
    # Prefer configured port, then fall back to the other Gmail-compatible option
    ports_to_try = [port]
    for alt in (465, 587):
        if alt not in ports_to_try:
            ports_to_try.append(alt)

    for try_port in ports_to_try:
        try:
            _smtp_send(host, try_port, user, password, message)
            msg = f"Verification email sent to {to_email} via {host}:{try_port}"
            print(msg, flush=True)
            logger.info(msg)
            return
        except (smtplib.SMTPException, OSError) as exc:
            err = f"{host}:{try_port} → {exc}"
            errors.append(err)
            logger.warning("SMTP attempt failed: %s", err)

    raise EmailSendError(
        "Не удалось отправить письмо. "
        + " | ".join(errors)
        + ". Проверьте пароль приложения и сеть (антивирус/VPN). "
        "Если используете Gmail и ошибка TLS — попробуйте Яндекс (smtp.yandex.ru:465)."
    )
