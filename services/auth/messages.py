# Uses PEP 8
# Tools: black, flake8, mypy

"""Shared Russian user-facing auth messages (bot + docs; web mirrors in TS)."""

from auth.email_domains import DOMAIN_ERROR_RU

INVALID_EMAIL_RU = "Укажите корректный email."
ALLOWED_DOMAINS_HINT_RU = "@spbstu.ru или @edu.spbstu.ru"

LOGIN_EMAIL_PROMPT_RU = "Введите email, указанный при регистрации на сайте:"
REGISTER_EMAIL_PROMPT_RU = (
    f"Регистрация в боте.\n\nВведите корпоративный email ({ALLOWED_DOMAINS_HINT_RU}):"
)
EMAIL_NOT_FOUND_RU = "Пользователь с таким email не найден."
EMAIL_ALREADY_EXISTS_RU = "Пользователь с таким email уже зарегистрирован."
REGISTER_EXISTS_WEB_HINT_RU = (
    f"{EMAIL_ALREADY_EXISTS_RU} Войдите в аккаунт."
)
REGISTER_EXISTS_BOT_HINT_RU = (
    f"{EMAIL_ALREADY_EXISTS_RU}\n\nВойдите: /login"
)
PASSWORD_PROMPT_RU = "Введите пароль:"
REGISTER_PASSWORD_MIN_RU = "Пароль должен быть не короче 6 символов."
WRONG_PASSWORD_RU = "Неверный пароль."
TELEGRAM_LINKED_OTHER_ACCOUNT_RU = (
    "Этот Telegram уже привязан к другому веб-аккаунту."
)
WEB_LINKED_OTHER_TELEGRAM_RU = (
    "К этому email уже привязан другой Telegram. "
    "Сначала выйдите в боте: /logout"
)
LOGIN_SERVER_ERROR_RU = (
    "Внутренняя ошибка сервера при входе. "
    "Проверьте, что применены миграции 005 и 008."
)
LOGIN_DB_CONFLICT_RU = (
    "Не удалось привязать Telegram из-за конфликта в базе. "
    "Выполните /logout и войдите снова."
)
CAPTCHA_REQUIRED_RU = "Подтвердите, что вы не робот."
CAPTCHA_FAILED_RU = "Проверка капчи не пройдена. Обновите страницу и попробуйте снова."

__all__ = [
    "DOMAIN_ERROR_RU",
    "INVALID_EMAIL_RU",
    "ALLOWED_DOMAINS_HINT_RU",
    "LOGIN_EMAIL_PROMPT_RU",
    "REGISTER_EMAIL_PROMPT_RU",
    "EMAIL_NOT_FOUND_RU",
    "EMAIL_ALREADY_EXISTS_RU",
    "REGISTER_EXISTS_BOT_HINT_RU",
    "REGISTER_EXISTS_WEB_HINT_RU",
    "PASSWORD_PROMPT_RU",
    "REGISTER_PASSWORD_MIN_RU",
    "WRONG_PASSWORD_RU",
    "TELEGRAM_LINKED_OTHER_ACCOUNT_RU",
    "WEB_LINKED_OTHER_TELEGRAM_RU",
]
