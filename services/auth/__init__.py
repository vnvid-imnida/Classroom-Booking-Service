# Shared auth helpers for backend and Telegram bot.

from auth.email_domains import (
    ALLOWED_EMAIL_DOMAINS,
    DOMAIN_ERROR_RU,
    is_allowed_spbstu_email,
    normalize_email,
    validate_spbstu_email,
)

__all__ = [
    "ALLOWED_EMAIL_DOMAINS",
    "DOMAIN_ERROR_RU",
    "is_allowed_spbstu_email",
    "normalize_email",
    "validate_spbstu_email",
]
