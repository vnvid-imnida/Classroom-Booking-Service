# Uses PEP 8
# Tools: black, flake8, mypy

"""Notify organizers when RUZ sync cancels their MANUAL booking."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from email_utils import EmailSendError, send_email
from telegram_utils import TelegramSendError, send_telegram_message

logger = logging.getLogger(__name__)

try:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    MOSCOW_TZ = timezone(timedelta(hours=3))

RUZ_OVERRIDE_REASON = (
    "Автоматическая отмена: в официальном расписании (RUZ) "
    "на это время в аудитории назначено занятие."
)


def _format_moscow(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")


def _room_label(ctx: dict) -> str:
    code = ctx.get("building_code") or ""
    number = ctx.get("room_number") or ""
    if code and number:
        return f"{code}-{number}"
    return number or code or "—"


def notify_ruz_override_cancel(ctx: dict, *, lesson_title: str | None = None) -> None:
    """Email + Telegram: MANUAL booking was cancelled because a RUZ lesson appeared."""
    name = ctx.get("full_name") or "пользователь"
    reason = ctx.get("cancel_reason") or RUZ_OVERRIDE_REASON
    lesson = (lesson_title or "").strip()
    subject = "Бронирование отменено (расписание) — SPbPU Booking"
    body_lines = [
        f"Здравствуйте, {name}!",
        "",
        "Ваше бронирование автоматически отменено.",
        f"Причина: {reason}",
    ]
    if lesson:
        body_lines.append(f"Занятие в расписании: {lesson}")
    body_lines.extend(
        [
            f"Название заявки: {ctx.get('title') or '—'}",
            f"Аудитория: {_room_label(ctx)}",
            f"Начало: {_format_moscow(ctx.get('starts_at'))} (МСК)",
            f"Конец: {_format_moscow(ctx.get('ends_at'))} (МСК)",
            "",
            "—",
            "SPbPU Classroom Booking",
        ]
    )
    body = "\n".join(body_lines)

    email = (ctx.get("email") or "").strip()
    if email:
        try:
            send_email(to_email=email, subject=subject, body=body)
        except EmailSendError as exc:
            logger.error("RUZ-override email failed for booking %s: %s", ctx.get("booking_id"), exc)

    tg_id = ctx.get("telegram_id")
    if tg_id:
        try:
            send_telegram_message(chat_id=tg_id, text=body)
        except TelegramSendError as exc:
            logger.error("RUZ-override Telegram failed for booking %s: %s", ctx.get("booking_id"), exc)
    elif not email:
        logger.info(
            "Skip RUZ-override notify for booking %s — no email and no telegram_id",
            ctx.get("booking_id"),
        )
