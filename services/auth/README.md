# Shared auth module (`services/auth`)

Single source of truth for **email domain rules**, **roles**, **messages**, and **API paths**.
HTTP handlers live in `services/backend/app.py`; bot and web are thin clients.

| Module | Purpose |
|--------|---------|
| `email_domains.py` | `@spbstu.ru` / `@edu.spbstu.ru`, validation, `role_for_email()` |
| `roles.py` | DB role constants, `effective_role()`, Russian role labels |
| `messages.py` | Russian UX strings (bot; frontend mirrors in `emailDomains.ts`) |
| `paths.py` | `/api/v1/auth/*` path constants |

**Bot-specific (not here):** FSM states, inline keyboards, `AuthMiddleware`, `X-Telegram-Id` headers.

**Backend:** imports `auth.*`; JWT and password hashing live in `services/backend/auth_utils.py`.

### Password hashing

- Passwords: **bcrypt** (12 rounds by default, override with `BCRYPT_ROUNDS`).
- Stored format: `$2b$12$...` (60-char bcrypt string).
- Web and Telegram bot use the same register/login API — no client-side hashing.
