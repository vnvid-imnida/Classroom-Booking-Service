# REST API contract (backend ↔ clients)

Base URL: `BACKEND_URL` (default `http://backend:8083`).

**Unified auth:** business rules in `services/auth/`; HTTP handlers in `services/backend/app.py`.
Web (`services/frontend`) and Telegram bot (`services/telegram-frontend`) call the same `/api/v1/auth/*` endpoints.

Auth (choose one):

- **Telegram bot**: `X-Telegram-Id: <telegram_id>` after linking.
- **Web**: `Authorization: Bearer <jwt>` from login/register.

Public (no auth): `/health`, `POST /api/v1/auth/register`, `POST /api/v1/auth/login` (optional `X-Telegram-Id` to bind bot), `POST /api/v1/users/link-telegram` (requires `X-Telegram-Id` only).

Web UI: React SPA at `services/frontend` (`/register`, `/login`). Bot login: `/login` in chat → `POST /api/v1/auth/login` with `X-Telegram-Id`. See `docs/BOT_LOGIN.md`.

## Users & auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Web signup (`email`, `password`, `full_name`) → JWT |
| POST | `/api/v1/auth/login` | Web login → JWT; with `X-Telegram-Id` also binds Telegram |
| POST | `/api/v1/auth/telegram-webapp` | Legacy: link via JWT after Web App (deprecated) |
| POST | `/api/v1/auth/link-token` | One-time Telegram link token (Bearer JWT) |
| POST | `/api/v1/users/link-telegram` | Bind Telegram to web user (`token` + `X-Telegram-Id`) |
| POST | `/api/v1/users/register` | Legacy Telegram-only upsert |
| GET | `/api/v1/me` | Current user |

Web register/login body:
```json
{ "email": "teacher@spbstu.ru", "password": "secret12", "full_name": "Иван Иванов" }
```

Email domain: only `@spbstu.ru` and `@edu.spbstu.ru` (validated in `services/auth/email_domains.py` and `POST /api/v1/auth/register`).

Login errors:
- `404` — user not found (`"Пользователь с таким email не найден"`)
- `401` — wrong password (`"Неверный пароль"`)
- `409` — email already registered (register): `"Пользователь с таким email уже зарегистрирован."`
- `400` — invalid email domain (register)

Link token response:
```json
{
  "token": "abc…",
  "expires_at": "2026-05-20T12:30:00+00:00",
  "bot_command": "/start link_abc…",
  "expires_in_minutes": 30
}
```

Bot: send `bot_command` or deep-link `https://t.me/<bot>?start=link_<token>`.

### Telegram bot login (preferred)

1. User registers on site (`FRONTEND_URL/register`).
2. In bot: `/login` → email → password.
3. Bot calls `POST /api/v1/auth/login` with body `{ email, password }` and headers `X-Telegram-Id`, `X-Telegram-Username`.
4. Backend verifies password, sets `users.telegram_id`, returns JWT and user; bot shows main menu.

Optional: `/start link_<token>` from site cabinet (`POST /api/v1/auth/link-token`).

Errors `409`: Telegram already linked to another user, or web account already linked to a different Telegram.

Env:

| Variable | Service | Description |
|----------|---------|-------------|
| `FRONTEND_URL` | bot | Frontend URL for registration hint (dev: `http://localhost:5173`) |
| `JWT_SECRET` | backend | JWT signing |

Legacy Telegram register:
```json
{
  "telegram_id": 1333800382,
  "telegram_username": "@user",
  "full_name": "Иван Иванов"
}
```

## Catalog

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/buildings` | List buildings |
| GET | `/api/v1/rooms` | Filter rooms (`building_code`, `min_capacity`, `has_projector`, `has_whiteboard`, `is_accessible`) |
| GET | `/api/v1/rooms/available` | Free rooms in interval (`starts_at`, `ends_at`, optional `building_code`) |
| GET | `/api/v1/event-purposes` | Event purpose dictionary |
| GET | `/api/v1/rooms/{room_id}/occupancy` | Active bookings + pending requests for room (`date=YYYY-MM-DD`) |

Occupancy slot (`source`: `booking` \| `pending_request`):
```json
{
  "id": "uuid",
  "room_id": 1,
  "title": "Собрание кафедры",
  "source": "pending_request",
  "status": "PENDING",
  "starts_at": "2026-05-21T10:00:00+00:00",
  "ends_at": "2026-05-21T12:00:00+00:00"
}
```

## Booking requests (teacher)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/booking-requests` | Create `DRAFT` (`action`: `CREATE` \| `RESCHEDULE`) |
| POST | `/api/v1/booking-requests/{id}/submit` | `DRAFT` → `PENDING` |
| POST | `/api/v1/booking-requests/{id}/cancel` | `DRAFT` \| `PENDING` → `CANCELLED` (owner only) |
| GET | `/api/v1/booking-requests/me?scope=active\|archive` | Own requests (`active`: draft/pending; `archive`: cancelled/rejected/approved) |

Create body:
```json
{
  "room_id": 1,
  "purpose_id": 1,
  "title": "Собрание кафедры",
  "description": "",
  "starts_at": "2026-05-21T10:00:00+00:00",
  "ends_at": "2026-05-21T12:00:00+00:00",
  "action": "CREATE",
  "target_booking_id": null
}
```

## Bookings (teacher cabinet)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/bookings/me?scope=active\|archive` | Personal bookings |
| POST | `/api/v1/bookings/{id}/cancel` | Cancel if >24h before start |

## Moderation (`role=MODERATOR`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/moderation/requests` | `PENDING` queue |
| POST | `/api/v1/moderation/requests/{id}/approve` | Approve → create `bookings` row |
| POST | `/api/v1/moderation/requests/{id}/reject` | Reject with optional `comment` |

## Errors

JSON: `{"detail": "human readable message"}`, HTTP 4xx/5xx.

Status transitions are enforced only in backend (see `DB_SCHEMA.md`).
