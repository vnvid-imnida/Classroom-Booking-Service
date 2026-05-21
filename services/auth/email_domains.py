# Uses PEP 8
# Tools: black, flake8, mypy

"""SPbPU corporate email domain rules shared by backend and Telegram bot."""

ALLOWED_EMAIL_DOMAINS: tuple[str, ...] = ("spbstu.ru", "edu.spbstu.ru")

DOMAIN_ERROR_RU = (
    "Регистрация доступна только для корпоративной почты "
    "@spbstu.ru или @edu.spbstu.ru"
)


def normalize_email(email: str) -> str:
    """Strip and lower-case an email address."""
    return email.strip().lower()


def email_domain(email: str) -> str | None:
    """Extract the domain part of an email, or None if invalid."""
    normalized = normalize_email(email)
    if "@" not in normalized:
        return None
    local, domain = normalized.rsplit("@", 1)
    if not local or not domain or "." not in domain:
        return None
    return domain


def is_allowed_spbstu_email(email: str) -> bool:
    """Return True when the email domain is an allowed SPbPU domain."""
    domain = email_domain(email)
    return domain in ALLOWED_EMAIL_DOMAINS if domain else False


def validate_spbstu_email(email: str) -> tuple[bool, str | None]:
    """Validate email format and SPbPU domain.

    Returns:
        ``(True, None)`` when valid, otherwise ``(False, Russian error message)``.
    """
    normalized = normalize_email(email)
    if not normalized or "@" not in normalized:
        return False, "Укажите корректный email."
    if not is_allowed_spbstu_email(normalized):
        return False, DOMAIN_ERROR_RU
    return True, None
