# Uses PEP 8
# Tools: black, flake8, mypy

from datetime import date, datetime, timedelta, timezone

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.api.client import BackendClient


def main_menu(is_moderator: bool = False) -> ReplyKeyboardMarkup:
    """Build the main reply keyboard; adds moderation row for moderators.

    Args:
        is_moderator: When True, include the moderation button.

    Returns:
        Reply keyboard markup for the main menu.
    """
    rows = [
        [KeyboardButton(text="📅 Новая заявка")],
        [KeyboardButton(text="🔍 Аудитории"), KeyboardButton(text="📋 Мои заявки")],
        [KeyboardButton(text="📚 Мои брони"), KeyboardButton(text="🗓 Занятость")],
    ]
    if is_moderator:
        rows.append([KeyboardButton(text="✅ Модерация")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_kb() -> InlineKeyboardMarkup:
    """Inline keyboard with a single cancel action."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]]
    )


def buildings_kb(buildings: list) -> InlineKeyboardMarkup:
    """Inline keyboard listing buildings by code.

    Args:
        buildings: Building dicts with ``code`` field.

    Returns:
        Inline keyboard for building selection.
    """
    rows = [
        [InlineKeyboardButton(text=f"Корпус {b['code']}", callback_data=f"bld:{b['code']}")]
        for b in buildings
    ]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rooms_kb(rooms: list, prefix: str = "room") -> InlineKeyboardMarkup:
    """Inline keyboard for room selection (up to 12 rooms).

    Args:
        rooms: Room dicts with building_code, room_number, capacity.
        prefix: Callback data prefix (e.g. ``room`` or ``occ_room``).

    Returns:
        Inline keyboard for room selection.
    """
    rows = []
    for room in rooms[:12]:
        label = f"{room['building_code']}-{room['room_number']} ({room['capacity']} мест)"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"{prefix}:{room['id']}")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


PURPOSE_LABELS = {
    "LECTURE": "Лекция",
    "EXAM": "Экзамен",
    "MEETING": "Собрание",
}


def purposes_kb(purposes: list) -> InlineKeyboardMarkup:
    """Inline keyboard for event purpose selection.

    Args:
        purposes: Purpose dicts with ``code``, ``name``, and ``id``.

    Returns:
        Inline keyboard for purpose selection.
    """
    rows = [
        [
            InlineKeyboardButton(
                text=PURPOSE_LABELS.get(p.get("code"), p.get("name", "Цель")),
                callback_data=f"purpose:{p['id']}",
            )
        ]
        for p in purposes
    ]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


FIXED_TIME_SLOTS = [
    ("09:00", "11:20"),
    ("11:30", "13:50"),
    ("14:00", "16:20"),
    ("16:30", "18:50"),
]


def date_kb(prefix: str = "date") -> InlineKeyboardMarkup:
    """Inline keyboard with the next seven calendar days.

    Args:
        prefix: Callback data prefix for date buttons.

    Returns:
        Inline keyboard for date selection.
    """
    rows = []
    today = date.today()
    for i in range(1, 8):
        d = today + timedelta(days=i)
        rows.append(
            [InlineKeyboardButton(text=d.strftime("%d.%m.%Y"), callback_data=f"{prefix}:{d.isoformat()}")]
        )
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def date_kb_filtered(
    room_id: int,
    api: BackendClient,
    *,
    prefix: str = "date",
    days_ahead: int = 14,
) -> InlineKeyboardMarkup | None:
    """Build date keyboard skipping Sundays and fully booked days.

    Args:
        room_id: Room to check occupancy for.
        api: Backend client for occupancy queries.
        prefix: Callback data prefix.
        days_ahead: How many days ahead to scan.

    Returns:
        Inline keyboard markup, or None when no dates are available.
    """
    rows = []
    today = date.today()
    for i in range(1, days_ahead + 1):
        d = today + timedelta(days=i)
        if d.weekday() == 6:
            continue
        date_str = d.isoformat()
        occupancy = await api.room_occupancy(room_id, date_str)
        if not free_slots_for_date(date_str, occupancy):
            continue
        rows.append(
            [InlineKeyboardButton(text=d.strftime("%d.%m.%Y"), callback_data=f"{prefix}:{date_str}")]
        )
    if not rows:
        return None
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def slot_callback_data(prefix: str, start_hm: str, end_hm: str) -> str:
    """Encode a time slot in pipe-separated callback data.

    Args:
        prefix: Callback prefix (e.g. ``slot``).
        start_hm: Slot start as ``HH:MM``.
        end_hm: Slot end as ``HH:MM``.

    Returns:
        Callback data string safe for times containing ``:``.
    """
    return f"{prefix}|{start_hm}|{end_hm}"


def parse_slot_callback(data: str, prefix: str = "slot") -> tuple[str, str] | None:
    """Parse start/end times from slot callback data.

    Args:
        data: Raw callback_data from an inline button.
        prefix: Expected callback prefix.

    Returns:
        ``(start_hm, end_hm)`` tuple, or None if format is invalid.
    """
    if not data.startswith(f"{prefix}|"):
        return None
    parts = data.split("|", 2)
    if len(parts) != 3:
        return None
    return parts[1], parts[2]


def _parse_api_dt(value: str) -> datetime:
    """Parse API ISO datetime to aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _slot_range(date_str: str, start_hm: str, end_hm: str) -> tuple[datetime, datetime]:
    """Build UTC datetime range for a fixed slot on a calendar day."""
    start = datetime.fromisoformat(f"{date_str}T{start_hm}:00").replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(f"{date_str}T{end_hm}:00").replace(tzinfo=timezone.utc)
    return start, end


def _ranges_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
    """Return True when two half-open intervals overlap."""
    return start1 < end2 and end1 > start2


def free_slots_for_date(date_str: str, occupancy: list) -> list[tuple[str, str]]:
    """List fixed time slots that do not overlap room occupancy.

    Args:
        date_str: Calendar day in ``YYYY-MM-DD`` format.
        occupancy: Occupancy records from the backend API.

    Returns:
        List of ``(start_hm, end_hm)`` pairs still available.
    """
    free = []
    for start_hm, end_hm in FIXED_TIME_SLOTS:
        slot_start, slot_end = _slot_range(date_str, start_hm, end_hm)
        blocked = False
        for occ in occupancy:
            occ_start = _parse_api_dt(occ["starts_at"])
            occ_end = _parse_api_dt(occ["ends_at"])
            if _ranges_overlap(slot_start, slot_end, occ_start, occ_end):
                blocked = True
                break
        if not blocked:
            free.append((start_hm, end_hm))
    return free


def time_slots_kb(
    prefix: str = "slot",
    slots: list[tuple[str, str]] | None = None,
) -> InlineKeyboardMarkup:
    """Inline keyboard for choosing a time slot.

    Args:
        prefix: Callback data prefix.
        slots: Optional slot list; defaults to ``FIXED_TIME_SLOTS``.

    Returns:
        Inline keyboard for time selection.
    """
    slot_list = slots if slots is not None else FIXED_TIME_SLOTS
    rows = [
        [InlineKeyboardButton(text=f"{s} — {e}", callback_data=slot_callback_data(prefix, s, e))]
        for s, e in slot_list
    ]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb(request_id: str) -> InlineKeyboardMarkup:
    """Confirm/submit keyboard for a draft booking request."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить на модерацию", callback_data=f"submit:{request_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
        ]
    )


def request_actions_kb(request_id: str, status: str | None = None) -> InlineKeyboardMarkup:
    """Actions for a single booking request (submit draft or cancel)."""
    rows = []
    if status == "DRAFT":
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Отправить заявку",
                    callback_data=f"submit_request:{request_id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отменить заявку",
                callback_data=f"cancel_request:{request_id}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_requests_nav_kb(*, show_archive: bool = True) -> InlineKeyboardMarkup:
    """Toggle between active requests list and archive."""
    button = (
        InlineKeyboardButton(text="📁 Архив заявок", callback_data="my_req:archive")
        if show_archive
        else InlineKeyboardButton(text="◀️ Активные заявки", callback_data="my_req:active")
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def booking_actions_kb(booking_id: str) -> InlineKeyboardMarkup:
    """Inline keyboard to cancel an active booking."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить бронь", callback_data=f"cancel_booking:{booking_id}")],
        ]
    )


def moderation_kb(request_id: str) -> InlineKeyboardMarkup:
    """Approve/reject inline keyboard for moderators."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"mod_approve:{request_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"mod_reject:{request_id}"),
            ],
        ]
    )
