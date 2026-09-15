# Uses PEP 8
# Tools: black, flake8, mypy

"""DB role constants and domain-based role resolution."""

from auth.email_domains import is_allowed_spbstu_email, role_for_email

ROLE_TEACHER = "TEACHER"
ROLE_STUDENT = "STUDENT"
ROLE_MODERATOR = "MODERATOR"
ROLE_ADMIN = "ADMIN"
ROLE_SYSTEM = "SYSTEM"

ELEVATED_ROLES = frozenset({ROLE_MODERATOR, ROLE_ADMIN, ROLE_SYSTEM})

ROLE_LABEL_RU = {
    ROLE_STUDENT: "Студент",
    ROLE_TEACHER: "Преподаватель",
    ROLE_MODERATOR: "Модератор",
    ROLE_ADMIN: "Администратор",
    ROLE_SYSTEM: "Система",
}


def effective_role(row: dict) -> str:
    """Resolve role for API responses; align TEACHER/STUDENT with email domain.

    Elevated roles are kept. For corporate emails, domain policy overrides stale DB rows.
    """
    stored = row.get("role") or ROLE_TEACHER
    if stored in ELEVATED_ROLES:
        return stored
    email = row.get("email")
    if email and is_allowed_spbstu_email(str(email)):
        return role_for_email(str(email))
    return stored


def role_label_ru_for_email(email: str) -> str | None:
    """Russian UI label implied by email domain (student / teacher)."""
    if not is_allowed_spbstu_email(email):
        return None
    db_role = role_for_email(email)
    return ROLE_LABEL_RU.get(db_role)
