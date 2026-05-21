# Uses PEP 8
# Tools: black, flake8, mypy

"""REST paths for unified web + Telegram auth (implemented in services/backend)."""

AUTH_REGISTER = "/api/v1/auth/register"
AUTH_LOGIN = "/api/v1/auth/login"
AUTH_CHECK_EMAIL = "/api/v1/auth/check-email"
AUTH_TELEGRAM_LOGOUT = "/api/v1/auth/telegram-logout"
AUTH_LINK_TOKEN = "/api/v1/auth/link-token"
AUTH_TELEGRAM_WEBAPP = "/api/v1/auth/telegram-webapp"
USERS_LINK_TELEGRAM = "/api/v1/users/link-telegram"
USERS_REGISTER_LEGACY = "/api/v1/users/register"
ME = "/api/v1/me"
