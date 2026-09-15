# Uses PEP 8
# Tools: black, flake8, mypy

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.api.client import BackendClient, BackendError
from bot.handlers.common import (
    client_from,
    client_from_callback,
    replace_flow_message,
    send_flow_message,
)
from bot.keyboards import (
    booking_actions_kb,
    buildings_kb,
    date_kb,
    my_requests_nav_kb,
    request_actions_kb,
    rooms_kb,
)
from bot.states import NewBooking, Occupancy

logger = logging.getLogger(__name__)
router = Router()

CANCELLABLE_REQUEST_STATUSES = frozenset({"DRAFT", "PENDING"})

STATUS_RU = {
    "DRAFT": "черновик",
    "PENDING": "на модерации",
    "CANCELLED": "отменена",
    "APPROVED": "одобрена",
    "REJECTED": "отклонена",
    "ACTIVE": "активна",
    "COMPLETED": "завершена",
    "RESCHEDULED": "перенесена",
}


def _fmt_dt(value: str) -> str:
    """Format API datetime for display in messages."""
    if not value:
        return "—"
    return str(value).replace("T", " ")[:16]


@router.message(F.text == "🔍 Аудитории")
async def search_rooms(message: Message, state: FSMContext):
    """Browse rooms by building (catalog, not booking FSM)."""
    await state.clear()
    try:
        buildings = await client_from(message).buildings()
    except BackendError as exc:
        await message.answer(f"Ошибка: {exc}")
        return
    await message.answer("Выберите корпус для просмотра аудиторий:", reply_markup=buildings_kb(buildings))


@router.callback_query(
    ~StateFilter(NewBooking),
    ~StateFilter(Occupancy),
    F.data.startswith("bld:"),
)
async def show_rooms_catalog(callback: CallbackQuery):
    """List rooms in a building with amenities (outside booking FSM)."""
    code = callback.data.split(":", 1)[1]
    try:
        rooms = await client_from_callback(callback).rooms(building_code=code)
    except BackendError as exc:
        await callback.answer(str(exc)[:200], show_alert=True)
        await callback.message.edit_text(f"Ошибка: {exc}")
        return
    if not rooms:
        await callback.answer("Аудитории не найдены", show_alert=True)
        await callback.message.edit_text("Аудитории не найдены.")
        return

    lines = [f"{rooms[0].get('building_name') or code}, аудитории:\n"]
    for r in rooms:
        flags = []
        if r.get("has_projector"):
            flags.append("проектор")
        if r.get("has_whiteboard"):
            flags.append("доска")
        if r.get("is_accessible"):
            flags.append("доступная")
        extra = ", ".join(flags) if flags else "без опций"
        lines.append(
            f"• {r['room_number']} (эт. {r['floor']}, {r['capacity']} мест) — {extra}"
        )
    await callback.answer()
    await callback.message.edit_text("\n".join(lines))


def _format_requests(title: str, items: list) -> str:
    """Build a text summary of booking requests."""
    lines = [f"{title}:\n"]
    for item in items:
        status = STATUS_RU.get(item.get("status", ""), item.get("status"))
        lines.append(
            f"• {item.get('title')}\n"
            f"  {item.get('building_code')}-{item.get('room_number')}, "
            f"{_fmt_dt(item.get('starts_at'))}\n"
            f"  Статус: {status}"
        )
    return "\n".join(lines)


async def _send_active_requests(message: Message, items: list) -> None:
    """Send active requests summary and per-item action keyboards."""
    cancellable = [i for i in items if i.get("status") in CANCELLABLE_REQUEST_STATUSES]
    if items:
        text = _format_requests("Активные заявки", items)
    else:
        text = "Нет активных заявок (черновики и заявки на модерации)."
    await message.answer(text, reply_markup=my_requests_nav_kb(show_archive=True))

    for item in cancellable[:5]:
        status = STATUS_RU.get(item.get("status", ""), item.get("status"))
        await message.answer(
            f"{item.get('title')}\n"
            f"{item.get('building_code')}-{item.get('room_number')}, "
            f"{_fmt_dt(item.get('starts_at'))}\n"
            f"Статус: {status}",
            reply_markup=request_actions_kb(item["id"], item.get("status")),
        )


@router.message(F.text == "📋 Мои заявки")
async def my_requests(message: Message):
    """Show active booking requests with archive navigation."""
    client = client_from(message)
    try:
        active = await client.my_requests("active")
        archive = await client.my_requests("archive")
    except BackendError as exc:
        await message.answer(f"Ошибка: {exc}")
        return
    if not active and not archive:
        await message.answer("У вас пока нет заявок.")
        return
    await _send_active_requests(message, active)


@router.callback_query(F.data == "my_req:archive")
async def my_requests_archive(callback: CallbackQuery, state: FSMContext):
    """Show archived booking requests."""
    try:
        items = await client_from_callback(callback).my_requests("archive")
    except BackendError as exc:
        await callback.answer(str(exc)[:200], show_alert=True)
        return

    await callback.answer()
    if not items:
        await replace_flow_message(
            callback,
            state,
            "Архив пуст.",
            reply_markup=my_requests_nav_kb(show_archive=False),
        )
        return

    await replace_flow_message(
        callback,
        state,
        _format_requests("Архив заявок", items),
        reply_markup=my_requests_nav_kb(show_archive=False),
    )


@router.callback_query(F.data == "my_req:active")
async def my_requests_active(callback: CallbackQuery, state: FSMContext):
    """Switch back to active requests list."""
    try:
        items = await client_from_callback(callback).my_requests("active")
    except BackendError as exc:
        await callback.answer(str(exc)[:200], show_alert=True)
        return

    await callback.answer()
    if items:
        text = _format_requests("Активные заявки", items)
    else:
        text = "Нет активных заявок (черновики и заявки на модерации)."
    await replace_flow_message(
        callback, state, text, reply_markup=my_requests_nav_kb(show_archive=True)
    )


@router.message(F.text == "📚 Мои брони")
async def my_bookings(message: Message):
    """Show active and archived confirmed bookings."""
    try:
        active = await client_from(message).my_bookings("active")
        archive = await client_from(message).my_bookings("archive")
    except BackendError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    if not active and not archive:
        await message.answer("Бронирований пока нет.")
        return

    if active:
        await message.answer(_format_bookings("Активные брони", active), reply_markup=None)
        for b in active[:5]:
            await message.answer(
                f"ID: {b['id'][:8]}…\n{b['title']}",
                reply_markup=booking_actions_kb(b["id"]),
            )

    if archive:
        await message.answer(_format_bookings("Архив", archive))


def _format_bookings(title: str, items: list) -> str:
    """Build a text summary of confirmed bookings."""
    lines = [f"{title}:\n"]
    for item in items:
        status = STATUS_RU.get(item.get("status", ""), item.get("status"))
        lines.append(
            f"• {item.get('title')}\n"
            f"  {item.get('building_code')}-{item.get('room_number')}, "
            f"{_fmt_dt(item.get('starts_at'))} — {status}"
        )
    return "\n".join(lines)


@router.callback_query(F.data.startswith("submit_request:"))
async def submit_request(callback: CallbackQuery):
    """Submit a draft request from the my-requests list."""
    request_id = callback.data.split(":", 1)[1]
    try:
        result = await client_from_callback(callback).submit_request(request_id)
    except BackendError as exc:
        await callback.answer(str(exc)[:200], show_alert=True)
        return
    status = STATUS_RU.get(result.get("status", ""), result.get("status", "PENDING"))
    await callback.answer("Заявка отправлена на модерацию")
    await callback.message.edit_text(
        f"Заявка отправлена на модерацию.\nСтатус: {status}"
    )


@router.callback_query(F.data.startswith("cancel_request:"))
async def cancel_request(callback: CallbackQuery):
    """Cancel a draft or pending request from the list."""
    request_id = callback.data.split(":", 1)[1]
    try:
        await client_from_callback(callback).cancel_request(request_id)
    except BackendError as exc:
        await callback.answer(str(exc)[:200], show_alert=True)
        return
    await callback.answer("Заявка отменена")
    await callback.message.edit_text("Заявка отменена.")


@router.callback_query(F.data.startswith("cancel_booking:"))
async def cancel_booking(callback: CallbackQuery):
    """Cancel an active booking (24h rule enforced by backend)."""
    booking_id = callback.data.split(":", 1)[1]
    try:
        await client_from_callback(callback).cancel_booking(booking_id)
    except BackendError as exc:
        await callback.answer(str(exc)[:200], show_alert=True)
        return
    await callback.answer("Бронь отменена")
    await callback.message.edit_text("Бронирование отменено.")


@router.message(F.text == "🗓 Занятость")
async def occupancy_start(message: Message, state: FSMContext):
    """Start occupancy view FSM: pick building."""
    await state.set_state(Occupancy.room)
    try:
        buildings = await client_from(message).buildings()
    except BackendError as exc:
        await message.answer(f"Ошибка: {exc}")
        return
    await send_flow_message(
        message, state, "Занятость: выберите корпус:", reply_markup=buildings_kb(buildings)
    )


@router.callback_query(Occupancy.room, F.data.startswith("bld:"))
async def occupancy_pick_building(callback: CallbackQuery, state: FSMContext):
    """Pick building for occupancy view."""
    code = callback.data.split(":", 1)[1]
    await state.update_data(building_code=code)
    try:
        rooms = await BackendClient(callback.from_user.id).rooms(building_code=code)
    except BackendError as exc:
        await callback.answer(str(exc)[:200], show_alert=True)
        await replace_flow_message(callback, state, f"Ошибка: {exc}")
        return

    await callback.answer()
    await replace_flow_message(
        callback,
        state,
        "Выберите аудиторию:",
        reply_markup=rooms_kb(rooms, prefix="occ_room"),
    )


@router.callback_query(Occupancy.room, F.data.startswith("occ_room:"))
async def occupancy_pick_room(callback: CallbackQuery, state: FSMContext):
    """Pick room and prompt for date."""
    room_id = int(callback.data.split(":", 1)[1])
    await state.update_data(room_id=room_id)
    await state.set_state(Occupancy.date)
    await callback.answer()
    await replace_flow_message(
        callback, state, "Выберите дату:", reply_markup=date_kb(prefix="occ_date")
    )


@router.callback_query(Occupancy.date, F.data.startswith("occ_date:"))
async def occupancy_show(callback: CallbackQuery, state: FSMContext):
    """Show occupancy slots for the selected room and day."""
    date_str = callback.data.split(":", 1)[1]
    data = await state.get_data()
    room_id = data["room_id"]
    try:
        slots = await client_from_callback(callback).room_occupancy(room_id, date_str)
    except BackendError as exc:
        await callback.answer(str(exc)[:200], show_alert=True)
        await replace_flow_message(callback, state, f"Ошибка: {exc}")
        return

    await state.clear()
    await callback.answer()
    if not slots:
        await replace_flow_message(
            callback, state, f"На {date_str} аудитория свободна.", track=False
        )
        return

    lines = [f"Занятость на {date_str}:\n"]
    for s in slots:
        title = s.get("title") or "—"
        if s.get("source") == "pending_request":
            desc = f"заявка на рассмотрении: {title}"
        else:
            desc = f"{title} ({s.get('source')})"
        lines.append(
            f"• {_fmt_dt(s.get('starts_at'))} — {_fmt_dt(s.get('ends_at'))}\n"
            f"  {desc}"
        )
    await replace_flow_message(callback, state, "\n".join(lines), track=False)
