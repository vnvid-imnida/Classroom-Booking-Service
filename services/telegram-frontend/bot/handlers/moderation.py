# Uses PEP 8
# Tools: black, flake8, mypy

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.api.client import BackendError
from bot.handlers.common import client_from, client_from_callback
from bot.keyboards import moderation_kb

logger = logging.getLogger(__name__)
router = Router()


def _fmt_dt(value: str) -> str:
    """Format API datetime for moderator messages."""
    return str(value).replace("T", " ")[:16] if value else "—"


@router.message(F.text == "✅ Модерация")
async def moderation_menu(message: Message):
    """List pending requests for moderators with approve/reject buttons."""
    try:
        queue = await client_from(message).moderation_queue()
    except BackendError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    if not queue:
        await message.answer("Очередь модерации пуста.")
        return

    await message.answer(f"Заявок на модерации: {len(queue)}")
    for item in queue[:10]:
        text = (
            f"Заявка: {item.get('title')}\n"
            f"От: {item.get('requester_name')} ({item.get('telegram_username')})\n"
            f"Аудитория: {item.get('building_code')}-{item.get('room_number')}\n"
            f"Цель: {item.get('purpose_name')}\n"
            f"Время: {_fmt_dt(item.get('starts_at'))} — {_fmt_dt(item.get('ends_at'))}"
        )
        await message.answer(text, reply_markup=moderation_kb(item["id"]))


@router.callback_query(F.data.startswith("mod_approve:"))
async def mod_approve(callback: CallbackQuery):
    """Approve a request from the moderation inline keyboard."""
    request_id = callback.data.split(":", 1)[1]
    try:
        result = await client_from_callback(callback).approve_request(request_id)
    except BackendError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.answer("Одобрено")
    booking = result.get("booking", {})
    await callback.message.edit_text(
        f"Заявка одобрена.\nБронь создана: {booking.get('id', '')[:8]}…"
    )


@router.callback_query(F.data.startswith("mod_reject:"))
async def mod_reject(callback: CallbackQuery):
    """Reject a request with a default moderator comment."""
    request_id = callback.data.split(":", 1)[1]
    try:
        await client_from_callback(callback).reject_request(request_id, comment="Отклонено модератором")
    except BackendError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.answer("Отклонено")
    await callback.message.edit_text("Заявка отклонена.")
