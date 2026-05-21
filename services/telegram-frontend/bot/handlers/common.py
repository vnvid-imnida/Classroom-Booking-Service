# Uses PEP 8
# Tools: black, flake8, mypy

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, ReplyKeyboardRemove

from bot.api.client import BackendClient, BackendError
from bot.keyboards import main_menu
from bot.states import BotLogin

logger = logging.getLogger(__name__)

router = Router()

FLOW_MSG_KEY = "last_bot_message_id"
ANSWER_KW = {"disable_web_page_preview": True}


async def store_flow_message(state: FSMContext, message_id: int) -> None:
    """Remember the latest bot message id for inline flow cleanup."""
    await state.update_data(**{FLOW_MSG_KEY: message_id})


async def delete_flow_message(bot, chat_id: int, state: FSMContext) -> None:
    """Delete the previously tracked flow message, if any."""
    data = await state.get_data()
    old_id = data.get(FLOW_MSG_KEY)
    if not old_id:
        return
    try:
        await bot.delete_message(chat_id, old_id)
    except TelegramBadRequest:
        pass
    await state.update_data(**{FLOW_MSG_KEY: None})


async def replace_flow_message(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    track: bool = True,
) -> int:
    """Edit inline flow step in place; fallback to delete + new message.

    Args:
        callback: Incoming callback query.
        state: FSM context for flow message tracking.
        text: Message text to show.
        reply_markup: Optional inline keyboard.
        track: When True, store message id for later cleanup.

    Returns:
        Message id of the displayed step.
    """
    chat_id = callback.message.chat.id
    msg_id = callback.message.message_id
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        mid = msg_id
    except TelegramBadRequest:
        await delete_flow_message(callback.bot, chat_id, state)
        try:
            await callback.bot.delete_message(chat_id, msg_id)
        except TelegramBadRequest:
            pass
        sent = await callback.message.answer(text, reply_markup=reply_markup, **ANSWER_KW)
        mid = sent.message_id
    if track:
        await store_flow_message(state, mid)
    return mid


async def send_flow_message(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardRemove | None = None,
) -> int:
    """Send a new flow step; removes previous tracked bot message.

    Returns:
        Message id of the sent step.
    """
    await delete_flow_message(message.bot, message.chat.id, state)
    sent = await message.answer(text, reply_markup=reply_markup, **ANSWER_KW)
    await store_flow_message(state, sent.message_id)
    return sent.message_id


async def try_delete_user_message(message: Message) -> None:
    """Best-effort delete of the user's message (e.g. password input)."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


def client_from(message: Message) -> BackendClient:
    """Build a backend client for the message sender."""
    return BackendClient(message.from_user.id)


def client_from_callback(callback: CallbackQuery) -> BackendClient:
    """Build a backend client from callback sender (not ``message.from_user``).

    On bot-sent inline keyboards ``message.from_user`` is the bot account.
    """
    return BackendClient(callback.from_user.id)


def _needs_web_auth(me: dict) -> bool:
    """Return True when the profile has no web email linked yet."""
    return not me.get("email")


_EMAIL_PROMPT = "Введите email, указанный при регистрации на сайте:"
_EMAIL_NOT_REGISTERED = "Такой пользователь не зарегистрирован.\n\n" + _EMAIL_PROMPT
_PASSWORD_PROMPT = "Введите пароль:"


def _login_welcome_text(*, partial_telegram: bool = False) -> str:
    """Welcome text for the in-bot login wizard."""
    text = (
        "👋 Привет! Это бот бронирования аудиторий СПбПУ.\n\n"
        "Заявки, брони и расписание — прямо в Telegram.\n"
        "Войдите email и паролем с сайта — и можно работать."
    )
    if partial_telegram:
        text += "\n\nℹ️ Telegram уже в системе, осталось привязать email с сайта."
    else:
        text += "\n\nНет аккаунта? Зарегистрируйтесь на сайте (см. /help)."
    return text


def _authorized_notice(me: dict) -> str:
    """Short notice shown when the user is already logged in."""
    email = me.get("email") or ""
    name = me.get("full_name") or "пользователь"
    parts = [f"✅ Вы уже авторизованы как {name}"]
    if email:
        parts[0] += f" ({email})"
    parts.append("\n\nМожно пользоваться меню ниже.")
    parts.append("Сменить аккаунт: /logout или /login.")
    return "".join(parts)


async def _bot_logout(message: Message, state: FSMContext) -> bool:
    """Clear FSM and unlink Telegram on the backend.

    Returns:
        True when a Telegram link existed and was removed.
    """
    await state.clear()
    api = client_from(message)
    try:
        await api.unlink_telegram()
        return True
    except BackendError as exc:
        if exc.status_code == 404:
            return False
        raise


async def _begin_login_wizard(
    message: Message, state: FSMContext, *, partial_telegram: bool = False
) -> None:
    """Start linear login prompts: welcome text then email step."""
    await message.answer(
        _login_welcome_text(partial_telegram=partial_telegram),
        reply_markup=ReplyKeyboardRemove(),
        **ANSWER_KW,
    )
    await message.answer(_EMAIL_PROMPT, **ANSWER_KW)
    await state.set_state(BotLogin.email)


async def _start_unlinked_login(
    message: Message, state: FSMContext, *, partial_telegram: bool = False
) -> None:
    """Redirect unlinked users into the email/password login wizard."""
    await _begin_login_wizard(message, state, partial_telegram=partial_telegram)


async def _show_main_menu(message: Message, me: dict) -> None:
    """Send greeting and main reply keyboard after successful auth."""
    is_moderator = me.get("role") in ("MODERATOR", "ADMIN")
    await message.answer(
        f"Добро пожаловать, {me.get('full_name', message.from_user.full_name)}!\n\n"
        "Бот бронирования аудиторий СПбПУ.\n"
        "Заявки, брони и занятость — в меню ниже.",
        reply_markup=main_menu(is_moderator),
        **ANSWER_KW,
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start: link token, existing session, or login wizard."""
    await state.clear()
    user = message.from_user
    api = client_from(message)
    args = (message.text or "").split(maxsplit=1)
    payload = args[1].strip() if len(args) > 1 else ""

    if payload.startswith("link_"):
        token = payload[5:].strip()
        if not token:
            await message.answer("Укажите токен: /start link_<токен>", **ANSWER_KW)
            return
        try:
            me = await api.link_telegram(
                token,
                telegram_username=user.username and f"@{user.username}" or None,
            )
        except BackendError as exc:
            await message.answer(f"Не удалось привязать Telegram: {exc}", **ANSWER_KW)
            return
        await message.answer("Telegram успешно привязан к вашему веб-аккаунту.", **ANSWER_KW)
        await _show_main_menu(message, me)
        return

    try:
        me = await api.me()
    except BackendError as exc:
        if exc.status_code == 404:
            await _begin_login_wizard(message, state)
            return
        detail = str(exc).strip() or "неизвестная ошибка"
        logger.exception("Start failed for telegram_id=%s", user.id)
        from bot.config import BACKEND_URL

        await message.answer(
            f"Ошибка: {detail}\n\nBackend: {BACKEND_URL}\n"
            "Запустите backend: cd services\\backend && python main.py",
            **ANSWER_KW,
        )
        return

    if _needs_web_auth(me):
        await _begin_login_wizard(message, state, partial_telegram=True)
        return

    await message.answer(_authorized_notice(me), **ANSWER_KW)
    is_moderator = me.get("role") in ("MODERATOR", "ADMIN")
    await message.answer(
        "Выберите действие:",
        reply_markup=main_menu(is_moderator),
        **ANSWER_KW,
    )


@router.message(Command("logout"))
async def cmd_logout(message: Message, state: FSMContext):
    """Unlink Telegram and clear local FSM state."""
    linked = await _bot_logout(message, state)
    if linked:
        text = (
            "Вы вышли из бота. Telegram отвязан от аккаунта.\n\n"
            "Чтобы войти снова — /start"
        )
    else:
        text = "Вы не были привязаны к аккаунту.\n\nЧтобы войти — /start"
    await message.answer(text, reply_markup=ReplyKeyboardRemove(), **ANSWER_KW)


@router.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext):
    """Reset session and restart the email/password login wizard."""
    await _bot_logout(message, state)
    await message.answer(
        "Сессия сброшена. Войдите с email и паролем с сайта.",
        **ANSWER_KW,
    )
    await _begin_login_wizard(message, state)


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    """Show bot usage help and registration URL."""
    from bot.config import FRONTEND_URL

    await message.answer(
        "Доступные действия:\n"
        "• Новая заявка — бронирование аудитории\n"
        "• Аудитории — поиск по корпусам\n"
        "• Мои заявки — статусы заявок на модерации\n"
        "• Мои брони — активные и архивные брони\n"
        "• Занятость — расписание аудитории на день\n"
        "• Модерация — для модераторов\n\n"
        f"Регистрация на сайте: {FRONTEND_URL}/register\n"
        "Вход: /start или /login (сброс и вход заново)\n"
        "Выход: /logout\n"
        "Привязка по коду: /start link_<код>\n\n"
        "Отмена брони возможна не позднее чем за 24 часа до начала.",
        **ANSWER_KW,
    )


@router.message(F.text.in_({"🔐 Войти (/login)", "🔐 Войти"}))
async def btn_login(message: Message, state: FSMContext):
    """Handle the reply-keyboard login button."""
    await cmd_login(message, state)


@router.message(BotLogin.email, ~F.text.startswith("/"))
async def bot_login_email(message: Message, state: FSMContext):
    """Collect and validate email during bot login."""
    email = (message.text or "").strip()
    if not email or "@" not in email:
        await message.answer(
            "Не удалось распознать адрес.\n" + _EMAIL_PROMPT,
            **ANSWER_KW,
        )
        return

    api = client_from(message)
    try:
        exists = await api.check_email_exists(email)
    except BackendError as exc:
        await message.answer(
            f"Не удалось проверить email: {exc}\n\n" + _EMAIL_PROMPT,
            **ANSWER_KW,
        )
        return
    if not exists:
        await message.answer(_EMAIL_NOT_REGISTERED, **ANSWER_KW)
        return

    await state.update_data(email=email)
    await message.answer(_PASSWORD_PROMPT, **ANSWER_KW)
    await state.set_state(BotLogin.password)


@router.message(BotLogin.password, ~F.text.startswith("/"))
async def bot_login_password(message: Message, state: FSMContext):
    """Submit password, call backend login, and show main menu on success."""
    password = message.text or ""
    if not password:
        await message.answer(_PASSWORD_PROMPT, **ANSWER_KW)
        return
    # Сразу убираем пароль из чата (анимацию даёт клиент Telegram).
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    data = await state.get_data()
    email = data.get("email", "")
    if not email:
        await message.answer(_EMAIL_PROMPT, **ANSWER_KW)
        await state.set_state(BotLogin.email)
        return
    user = message.from_user
    api = client_from(message)

    try:
        auth = await api.web_login(
            email,
            password,
            telegram_username=user.username and f"@{user.username}" or None,
        )
    except BackendError as exc:
        if exc.status_code == 409 and "already linked" in str(exc).lower():
            try:
                me = await api.me()
            except BackendError:
                me = None
            if me and (me.get("email") or "").strip().lower() == email.strip().lower():
                await state.clear()
                await message.answer(
                    "Вход выполнен, Telegram привязан к аккаунту.",
                    **ANSWER_KW,
                )
                await _show_main_menu(message, me)
                return
            await message.answer(_PASSWORD_PROMPT, **ANSWER_KW)
            return
        detail = str(exc).lower()
        if exc.status_code == 401 and "invalid email" in detail:
            await message.answer(_EMAIL_NOT_REGISTERED, **ANSWER_KW)
            await state.set_state(BotLogin.email)
            return
        await message.answer(
            "Неверный пароль. " + _PASSWORD_PROMPT,
            **ANSWER_KW,
        )
        return

    await state.clear()

    me = auth.get("user")
    if not me:
        try:
            me = await api.me()
        except BackendError as exc:
            await message.answer(f"Вход выполнен, но профиль не получен: {exc}", **ANSWER_KW)
            return

    await message.answer("Вход выполнен, Telegram привязан к аккаунту.", **ANSWER_KW)
    await _show_main_menu(message, me)


@router.message(F.text == "🏠 Меню")
async def back_to_menu(message: Message, state: FSMContext):
    """Return to main menu or run /start when mid-login."""
    current = await state.get_state()
    if current in (BotLogin.email.state, BotLogin.password.state):
        await cmd_start(message, state)
        return
    await state.clear()
    api = client_from(message)
    try:
        me = await api.me()
    except BackendError as exc:
        if exc.status_code == 404:
            await _begin_login_wizard(message, state)
            return
        await message.answer(f"Ошибка: {exc}", **ANSWER_KW)
        return
    if _needs_web_auth(me):
        await _begin_login_wizard(message, state, partial_telegram=True)
        return
    is_moderator = me.get("role") in ("MODERATOR", "ADMIN")
    await message.answer("Главное меню:", reply_markup=main_menu(is_moderator), **ANSWER_KW)
