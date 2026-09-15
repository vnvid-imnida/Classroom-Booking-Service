# Uses PEP 8
# Tools: black, flake8, mypy

import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.api.client import BackendClient, BackendError
from bot.handlers.common import (
    client_from,
    delete_flow_message,
    replace_flow_message,
    send_flow_message,
)
from bot.keyboards import (
    buildings_kb,
    confirm_kb,
    date_kb_filtered,
    free_slots_for_date,
    parse_slot_callback,
    purposes_kb,
    rooms_kb,
    time_slots_kb,
)
from bot.states import NewBooking

logger = logging.getLogger(__name__)
router = Router()


def _iso_range(date_str: str, start_hm: str, end_hm: str) -> tuple[str, str]:
    """Convert local slot times on a date to UTC ISO strings for the API."""
    starts_at = datetime.fromisoformat(f"{date_str}T{start_hm}:00").replace(tzinfo=timezone.utc)
    ends_at = datetime.fromisoformat(f"{date_str}T{end_hm}:00").replace(tzinfo=timezone.utc)
    return starts_at.isoformat(), ends_at.isoformat()


async def _show_booking_dates(callback: CallbackQuery, state: FSMContext, room_id: int) -> bool:
    """Show filtered date keyboard for the selected room.

    Returns:
        False when no dates are available (user is sent back to room pick).
    """
    api = BackendClient(callback.from_user.id)
    try:
        markup = await date_kb_filtered(room_id, api)
    except BackendError as exc:
        await replace_flow_message(callback, state, f"Ошибка: {exc}")
        return False

    if markup is None:
        data = await state.get_data()
        code = data.get("building_code")
        try:
            rooms = await api.rooms(building_code=code)
        except BackendError as exc:
            await replace_flow_message(callback, state, f"Ошибка: {exc}")
            return False
        await state.set_state(NewBooking.room)
        await replace_flow_message(
            callback,
            state,
            "Для этой аудитории нет свободных дат в ближайшие две недели "
            "(воскресенья и полностью занятые дни не показываются). Выберите другую аудиторию:",
            reply_markup=rooms_kb(rooms),
        )
        return False

    await state.set_state(NewBooking.date)
    await replace_flow_message(callback, state, "Выберите дату:", reply_markup=markup)
    return True


@router.message(F.text == "📅 Новая заявка")
async def new_booking_start(message: Message, state: FSMContext):
    """Start the new booking FSM: pick building."""
    await state.clear()
    await state.set_state(NewBooking.building)
    try:
        buildings = await client_from(message).buildings()
    except BackendError as exc:
        await message.answer(f"Ошибка: {exc}")
        return
    if not buildings:
        await message.answer("Корпуса не найдены. Обратитесь к администратору.")
        return
    await send_flow_message(
        message, state, "Выберите корпус:", reply_markup=buildings_kb(buildings)
    )


@router.callback_query(NewBooking.building, F.data.startswith("bld:"))
async def pick_building(callback: CallbackQuery, state: FSMContext):
    """Handle building selection and list rooms in that building."""
    await callback.answer()
    code = callback.data.split(":", 1)[1]
    await state.update_data(building_code=code)
    await state.set_state(NewBooking.room)
    try:
        rooms = await BackendClient(callback.from_user.id).rooms(building_code=code)
    except BackendError as exc:
        await replace_flow_message(callback, state, f"Ошибка: {exc}")
        return
    if not rooms:
        await replace_flow_message(callback, state, "В этом корпусе нет доступных аудиторий.")
        return
    building_name = rooms[0].get("building_name") or code
    await state.update_data(building_name=building_name)
    await replace_flow_message(
        callback,
        state,
        f"{building_name}. Выберите аудиторию:",
        reply_markup=rooms_kb(rooms),
    )


@router.callback_query(NewBooking.room, F.data.startswith("room:"))
async def pick_room(callback: CallbackQuery, state: FSMContext):
    """Handle room selection and show available dates."""
    room_id = int(callback.data.split(":", 1)[1])
    await state.update_data(room_id=room_id)
    await callback.answer()
    await _show_booking_dates(callback, state, room_id)


@router.callback_query(NewBooking.date, F.data.startswith("date:"))
async def pick_date(callback: CallbackQuery, state: FSMContext):
    """Handle date selection and show free time slots."""
    date_str = callback.data.split(":", 1)[1]
    data = await state.get_data()
    room_id = data["room_id"]
    await state.update_data(date=date_str)
    await callback.answer()

    api = BackendClient(callback.from_user.id)
    try:
        occupancy = await api.room_occupancy(room_id, date_str)
    except BackendError as exc:
        await replace_flow_message(callback, state, f"Ошибка: {exc}")
        return

    free = free_slots_for_date(date_str, occupancy)
    if not free:
        await _show_booking_dates(callback, state, room_id)
        return

    await state.set_state(NewBooking.time_slot)
    await state.update_data(free_slots=free)
    await replace_flow_message(
        callback,
        state,
        f"Дата {date_str}. Выберите время:",
        reply_markup=time_slots_kb(slots=free),
    )


@router.callback_query(NewBooking.time_slot, F.data.startswith("slot|"))
async def pick_slot(callback: CallbackQuery, state: FSMContext):
    """Handle time slot selection, verify availability, ask for purpose."""
    await callback.answer()
    parsed = parse_slot_callback(callback.data)
    data = await state.get_data()
    if not parsed:
        free = data.get("free_slots")
        await replace_flow_message(
            callback,
            state,
            "Некорректный слот времени. Выберите снова:",
            reply_markup=time_slots_kb(slots=free),
        )
        return
    start_hm, end_hm = parsed
    starts_at, ends_at = _iso_range(data["date"], start_hm, end_hm)
    await state.update_data(starts_at=starts_at, ends_at=ends_at, time_label=f"{start_hm}–{end_hm}")

    api = BackendClient(callback.from_user.id)
    try:
        rooms = await api.available_rooms(
            starts_at, ends_at, building_code=data.get("building_code")
        )
        room_id = data["room_id"]
        if not any(r["id"] == room_id for r in rooms):
            await replace_flow_message(
                callback,
                state,
                "Выбранная аудитория занята в это время. Выберите другую дату или время.",
            )
            await _show_booking_dates(callback, state, room_id)
            return
        purposes = await api.event_purposes()
    except BackendError as exc:
        await replace_flow_message(callback, state, f"Ошибка: {exc}")
        return

    await state.set_state(NewBooking.purpose)
    await replace_flow_message(
        callback, state, "Выберите цель мероприятия:", reply_markup=purposes_kb(purposes)
    )


@router.callback_query(NewBooking.purpose, F.data.startswith("purpose:"))
async def pick_purpose(callback: CallbackQuery, state: FSMContext):
    """Handle event purpose selection and prompt for title."""
    purpose_id = int(callback.data.split(":", 1)[1])
    await state.update_data(purpose_id=purpose_id)
    await state.set_state(NewBooking.title)
    await callback.answer()
    await replace_flow_message(
        callback, state, "Введите название мероприятия (до 200 символов):"
    )


@router.message(NewBooking.title)
async def enter_title(message: Message, state: FSMContext):
    """Create draft request from title and show confirmation keyboard."""
    title = (message.text or "").strip()
    if not title or len(title) > 200:
        await message.answer("Укажите короткое название (1–200 символов).")
        return

    data = await state.get_data()
    api = client_from(message)
    try:
        draft = await api.create_request(
            {
                "room_id": data["room_id"],
                "purpose_id": data["purpose_id"],
                "title": title,
                "description": "",
                "starts_at": data["starts_at"],
                "ends_at": data["ends_at"],
                "action": "CREATE",
            }
        )
    except BackendError as exc:
        await message.answer(f"Не удалось создать заявку: {exc}")
        return

    await state.update_data(request_id=draft["id"], title=title)
    await state.set_state(NewBooking.confirm)
    await delete_flow_message(message.bot, message.chat.id, state)
    await message.answer(
        f"Проверьте заявку:\n"
        f"• Название: {title}\n"
        f"• Дата: {data['date']}\n"
        f"• Время: {data.get('time_label', '')}\n"
        f"• Статус: черновик\n\n"
        "Отправить на модерацию?",
        reply_markup=confirm_kb(draft["id"]),
    )


@router.callback_query(NewBooking.confirm, F.data.startswith("submit:"))
async def submit_draft(callback: CallbackQuery, state: FSMContext):
    """Submit draft booking request for moderation."""
    request_id = callback.data.split(":", 1)[1]
    try:
        result = await BackendClient(callback.from_user.id).submit_request(request_id)
    except BackendError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await state.clear()
    await callback.answer()
    me = await BackendClient(callback.from_user.id).me()
    is_mod = me.get("role") in ("MODERATOR", "ADMIN")
    from bot.keyboards import main_menu

    await callback.message.edit_text(
        f"Заявка отправлена на модерацию.\nСтатус: {result.get('status', 'PENDING')}"
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu(is_mod))


@router.callback_query(F.data == "cancel")
async def cancel_flow(callback: CallbackQuery, state: FSMContext):
    """Cancel the current inline booking flow."""
    await callback.answer("Отменено")
    await replace_flow_message(callback, state, "Действие отменено.", track=False)
    await state.clear()
