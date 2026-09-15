# Uses PEP 8
# Tools: black, flake8, mypy

import asyncio
import logging
import os
import sys
from pathlib import Path

_services_root = Path(__file__).resolve().parent.parent
if str(_services_root) not in sys.path:
    sys.path.insert(0, str(_services_root))

_env_file = Path(__file__).resolve().parents[2] / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

# Прокси ломает доступ к api.telegram.org и localhost backend (httpx)
for _proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(_proxy_var, None)

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, MenuButtonDefault

BOT_MENU_COMMANDS = [
    BotCommand(command="start", description="Начать / главное меню"),
    BotCommand(command="login", description="Выйти и войти заново"),
    BotCommand(command="logout", description="Выйти из бота"),
    BotCommand(command="help", description="Справка"),
]

from bot.config import (
    BACKEND_URL,
    HEALTH_PORT,
    SERVICE_NAME,
    TELEGRAM_BOT_TOKEN,
    log_bot_config,
)
from bot.handlers import setup_routers

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def health_handler(_request: web.Request) -> web.Response:
    """Aiohttp health endpoint for container probes."""
    return web.json_response({"status": "healthy", "service": SERVICE_NAME})


async def start_health_server() -> web.AppRunner | None:
    """Start a lightweight HTTP server exposing ``/health``.

    Returns:
        App runner when the port is free, otherwise None.
    """
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HEALTH_PORT)
    try:
        await site.start()
    except OSError as exc:
        await runner.cleanup()
        logger.warning(
            "Health server on port %s not started (%s). "
            "Bot will run without /health (stop Docker telegram if port is busy).",
            HEALTH_PORT,
            exc,
        )
        return None
    logger.info("Health server on port %s", HEALTH_PORT)
    return runner


async def run_bot() -> None:
    """Configure bot menu commands and start long polling."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    log_bot_config()

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        scope = BotCommandScopeDefault()
        await bot.delete_my_commands(scope=scope)
        await bot.set_my_commands(BOT_MENU_COMMANDS, scope=scope)
        logger.info(
            "Menu commands set: /start /login /logout /help (%d)",
            len(BOT_MENU_COMMANDS),
        )
    except Exception as exc:
        logger.warning("Could not reset menu button or commands: %s", exc)

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(setup_routers())

    logger.info("Starting Telegram bot, backend=%s", BACKEND_URL)
    await dp.start_polling(bot)


async def main() -> None:
    """Run health server and Telegram polling; clean up on shutdown."""
    health_runner = await start_health_server()
    try:
        await run_bot()
    finally:
        if health_runner is not None:
            await health_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
