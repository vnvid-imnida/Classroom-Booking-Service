# Uses PEP 8
# Tools: black, flake8, mypy

from aiogram import Router

from bot.handlers import booking, cabinet, common, moderation
from bot.middleware.auth import AuthMiddleware


def setup_routers() -> Router:
    """Wire public and auth-protected handler routers.

    Returns:
        Root router with common routes and middleware-guarded booking flows.
    """
    root = Router()
    root.include_router(common.router)

    auth = AuthMiddleware()
    protected = Router()
    protected.message.middleware(auth)
    protected.callback_query.middleware(auth)
    protected.include_router(booking.router)
    protected.include_router(cabinet.router)
    protected.include_router(moderation.router)
    root.include_router(protected)
    return root
