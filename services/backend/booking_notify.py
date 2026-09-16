# Uses PEP 8
# Tools: black, flake8, mypy

"""Booking status/reminder notifications via email and Telegram."""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from db import execute, fetch_all, fetch_one, get_conn
from email_utils import EmailSendError, send_email
from telegram_utils import TelegramSendError, send_telegram_message

logger = logging.getLogger(__name__)

try:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    MOSCOW_TZ = timezone(timedelta(hours=3))

STATUS_LABELS_RU = {
    "PENDING": "на модерации",
    "APPROVED": "подтверждена",
    "REJECTED": "отклонена",
    "CANCELLED": "отменена",
    "ACTIVE": "активна",
}

_stop_reminders = threading.Event()
_reminder_thread: threading.Thread | None = None


def _format_moscow(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")


def notify_async(fn, *args, **kwargs) -> None:
    """Fire-and-forget so API latency stays within the 10s notification SLA window."""

    def _run() -> None:
        try:
            fn(*args, **kwargs)
        except Exception:  # noqa: BLE001 — never fail the HTTP handler because of notify
            logger.exception("Async notification failed")

    threading.Thread(target=_run, name="booking-notify", daemon=True).start()


def _load_request_context(conn, request_id: str) -> dict | None:
    return fetch_one(
        conn,
        """
        SELECT br.id::text AS request_id,
               br.title,
               br.status,
               br.starts_at,
               br.ends_at,
               br.moderation_comment,
               u.email,
               u.full_name,
               u.telegram_id,
               b.code AS building_code,
               r.room_number
        FROM booking_requests br
        JOIN users u ON u.id = br.requester_id
        JOIN rooms r ON r.id = br.room_id
        JOIN buildings b ON b.id = r.building_id
        WHERE br.id = %s::uuid
        """,
        (request_id,),
    )


def _load_booking_context(conn, booking_id: str) -> dict | None:
    return fetch_one(
        conn,
        """
        SELECT bk.id::text AS booking_id,
               bk.title,
               bk.status,
               bk.starts_at,
               bk.ends_at,
               u.email,
               u.full_name,
               u.telegram_id,
               b.code AS building_code,
               r.room_number
        FROM bookings bk
        JOIN users u ON u.id = bk.organizer_id
        JOIN rooms r ON r.id = bk.room_id
        JOIN buildings b ON b.id = r.building_id
        WHERE bk.id = %s::uuid
        """,
        (booking_id,),
    )


def _room_label(ctx: dict) -> str:
    code = ctx.get("building_code") or ""
    number = ctx.get("room_number") or ""
    if code and number:
        return f"{code}-{number}"
    return number or code or "—"


def _deliver(*, ctx: dict, subject: str, body: str) -> bool:
    """Send via email and/or Telegram. Returns True if at least one channel succeeded."""
    delivered = False
    email = (ctx.get("email") or "").strip()
    if email:
        try:
            send_email(to_email=email, subject=subject, body=body)
            delivered = True
        except EmailSendError as exc:
            logger.error("Email notify failed (%s): %s", subject, exc)

    tg_id = ctx.get("telegram_id")
    if tg_id:
        try:
            send_telegram_message(chat_id=tg_id, text=body)
            delivered = True
        except TelegramSendError as exc:
            logger.error("Telegram notify failed (%s): %s", subject, exc)
    elif not email:
        logger.info("Skip notify %r — no email and no telegram_id", subject)

    return delivered


def send_request_status_email(request_id: str, *, status: str | None = None) -> None:
    """Notify requester (email + Telegram) about a booking-request status change."""
    with get_conn() as conn:
        ctx = _load_request_context(conn, request_id)
    if not ctx:
        logger.warning("No request context for notify: %s", request_id)
        return

    st = (status or ctx.get("status") or "").upper()
    label = STATUS_LABELS_RU.get(st, st.lower())
    name = ctx.get("full_name") or "пользователь"
    subject = f"Заявка {label} — SPbPU Booking"
    body_lines = [
        f"Здравствуйте, {name}!",
        "",
        f"Статус вашей заявки на бронирование: {label}.",
        f"Название: {ctx.get('title') or '—'}",
        f"Аудитория: {_room_label(ctx)}",
        f"Начало: {_format_moscow(ctx.get('starts_at'))} (МСК)",
        f"Конец: {_format_moscow(ctx.get('ends_at'))} (МСК)",
    ]
    comment = (ctx.get("moderation_comment") or "").strip()
    if st == "REJECTED" and comment:
        body_lines.extend(["", f"Комментарий модератора: {comment}"])
    body_lines.extend(["", "—", "SPbPU Classroom Booking"])
    _deliver(ctx=ctx, subject=subject, body="\n".join(body_lines))


def send_booking_cancelled_email(booking_id: str) -> None:
    """Notify organizer (email + Telegram) that an active booking was cancelled."""
    with get_conn() as conn:
        ctx = _load_booking_context(conn, booking_id)
    if not ctx:
        return
    name = ctx.get("full_name") or "пользователь"
    subject = "Бронирование отменено — SPbPU Booking"
    body = (
        f"Здравствуйте, {name}!\n\n"
        f"Ваше бронирование отменено.\n"
        f"Название: {ctx.get('title') or '—'}\n"
        f"Аудитория: {_room_label(ctx)}\n"
        f"Начало: {_format_moscow(ctx.get('starts_at'))} (МСК)\n"
        f"Конец: {_format_moscow(ctx.get('ends_at'))} (МСК)\n\n"
        "—\nSPbPU Classroom Booking"
    )
    _deliver(ctx=ctx, subject=subject, body=body)


def send_booking_reminder(ctx: dict, *, hours_before: int) -> bool:
    """Send a 24h / 1h reminder via email and/or Telegram."""
    name = ctx.get("full_name") or "пользователь"
    subject = f"Напоминание за {hours_before} ч — SPbPU Booking"
    body = (
        f"Здравствуйте, {name}!\n\n"
        f"Напоминаем: до начала бронирования осталось около {hours_before} ч.\n"
        f"Название: {ctx.get('title') or '—'}\n"
        f"Аудитория: {_room_label(ctx)}\n"
        f"Начало: {_format_moscow(ctx.get('starts_at'))} (МСК)\n"
        f"Конец: {_format_moscow(ctx.get('ends_at'))} (МСК)\n\n"
        "—\nSPbPU Classroom Booking"
    )
    return _deliver(ctx=ctx, subject=subject, body=body)


def process_due_reminders() -> dict:
    """Send pending 24h/1h reminders for ACTIVE manual bookings."""
    sent_24h = 0
    sent_1h = 0
    with get_conn() as conn:
        due_24h = fetch_all(
            conn,
            """
            SELECT bk.id::text AS booking_id,
                   bk.title, bk.starts_at, bk.ends_at,
                   u.email, u.full_name, u.telegram_id,
                   b.code AS building_code, r.room_number
            FROM bookings bk
            JOIN users u ON u.id = bk.organizer_id
            JOIN rooms r ON r.id = bk.room_id
            JOIN buildings b ON b.id = r.building_id
            WHERE bk.status = 'ACTIVE'
              AND bk.source = 'MANUAL'
              AND bk.reminder_24h_sent_at IS NULL
              AND bk.starts_at > now()
              AND bk.starts_at <= now() + interval '24 hours'
              AND bk.starts_at > now() + interval '1 hour'
            """,
        )
        for row in due_24h:
            try:
                if send_booking_reminder(row, hours_before=24):
                    execute(
                        conn,
                        """
                        UPDATE bookings
                        SET reminder_24h_sent_at = now()
                        WHERE id = %s::uuid AND reminder_24h_sent_at IS NULL
                        """,
                        (row["booking_id"],),
                    )
                    sent_24h += 1
            except Exception:  # noqa: BLE001
                logger.exception("24h reminder failed for %s", row.get("booking_id"))

        due_1h = fetch_all(
            conn,
            """
            SELECT bk.id::text AS booking_id,
                   bk.title, bk.starts_at, bk.ends_at,
                   u.email, u.full_name, u.telegram_id,
                   b.code AS building_code, r.room_number
            FROM bookings bk
            JOIN users u ON u.id = bk.organizer_id
            JOIN rooms r ON r.id = bk.room_id
            JOIN buildings b ON b.id = r.building_id
            WHERE bk.status = 'ACTIVE'
              AND bk.source = 'MANUAL'
              AND bk.reminder_1h_sent_at IS NULL
              AND bk.starts_at > now()
              AND bk.starts_at <= now() + interval '1 hour'
            """,
        )
        for row in due_1h:
            try:
                if send_booking_reminder(row, hours_before=1):
                    execute(
                        conn,
                        """
                        UPDATE bookings
                        SET reminder_1h_sent_at = now()
                        WHERE id = %s::uuid AND reminder_1h_sent_at IS NULL
                        """,
                        (row["booking_id"],),
                    )
                    sent_1h += 1
            except Exception:  # noqa: BLE001
                logger.exception("1h reminder failed for %s", row.get("booking_id"))

    return {"sent_24h": sent_24h, "sent_1h": sent_1h}


def _reminder_loop() -> None:
    interval = int(os.getenv("BOOKING_REMINDER_POLL_SECONDS", "60"))
    interval = max(15, interval)
    if _stop_reminders.wait(10):
        return
    logger.info("Booking reminder loop started (every %ss)", interval)
    while not _stop_reminders.wait(interval):
        try:
            stats = process_due_reminders()
            if stats["sent_24h"] or stats["sent_1h"]:
                logger.info("Reminders sent: %s", stats)
        except Exception:  # noqa: BLE001
            logger.exception("Reminder loop iteration failed")


def start_reminder_scheduler() -> None:
    """Start background reminder poller (idempotent)."""
    global _reminder_thread
    if _reminder_thread and _reminder_thread.is_alive():
        return
    _stop_reminders.clear()
    _reminder_thread = threading.Thread(
        target=_reminder_loop, name="booking-reminders", daemon=True
    )
    _reminder_thread.start()


def stop_reminder_scheduler() -> None:
    _stop_reminders.set()
