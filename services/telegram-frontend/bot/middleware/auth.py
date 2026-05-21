# Uses PEP 8
# Tools: black, flake8, mypy

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from aiogram.fsm.context import FSMContext

from bot.api.client import BackendClient, BackendError
from bot.handlers.common import _needs_web_auth, _start_unlinked_login
from bot.states import BotLogin, BotRegister

logger = logging.getLogger(__name__)


async def _in_bot_login_wizard(state: FSMContext | None) -> bool:
    """Return True when the user is in the email/password login FSM.

    Args:
        state: Aiogram FSM context, if present.

    Returns:
        True while collecting email or password.
    """
    if state is None:
        return False
    current = await state.get_state()
    return current in (
        BotLogin.email.state,
        BotLogin.password.state,
        BotRegister.email.state,
        BotRegister.full_name.state,
        BotRegister.password.state,
    )


class AuthMiddleware(BaseMiddleware):
    """Block booking/cabinet/moderation until Telegram is linked to a web account."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Verify backend linkage before protected handlers run.

        Args:
            handler: Next middleware or route handler.
            event: Incoming Telegram update.
            data: Handler context dict (includes ``state`` when available).

        Returns:
            Handler result, or None when login wizard was started instead.

        Raises:
            BackendError: Re-raised for non-404 API failures.
        """
        user_id: int | None = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        if await _in_bot_login_wizard(data.get("state")):
            return await handler(event, data)

        try:
            me = await BackendClient(user_id).me()
        except BackendError as exc:
            if exc.status_code == 404:
                if isinstance(event, Message):
                    state = data.get("state")
                    if state is not None:
                        await _start_unlinked_login(event, state)
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "Сначала войдите: /login (email и пароль с сайта)",
                        show_alert=True,
                    )
                    if event.message:
                        state = data.get("state")
                        if state is not None:
                            await _start_unlinked_login(event.message, state)
                return None
            raise

        if _needs_web_auth(me):
            if isinstance(event, Message):
                state = data.get("state")
                if state is not None:
                    await _start_unlinked_login(event, state, partial_telegram=True)
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "Сначала войдите: /login (email и пароль с сайта)",
                    show_alert=True,
                )
                if event.message:
                    state = data.get("state")
                    if state is not None:
                        await _start_unlinked_login(
                            event.message, state, partial_telegram=True
                        )
            return None

        return await handler(event, data)
