# Backend (`services/backend`)

Основной REST API бронирования аудиторий СПбПУ. Клиенты: веб и Telegram-бот.

Порт: **8083** · Compose-сервис: `backend`

## Возможности

- Auth: регистрация, email-код, login/JWT, привязка Telegram (`X-Telegram-Id`)
- Каталог: корпуса, аудитории, поиск свободных слотов, занятость
- Заявки на бронирование: создание, submit, отмена; модерация approve/reject
- Кабинет: мои заявки и бронирования
- Админ: создание / soft-delete аудиторий
- Уведомления (async): **email (SMTP)** и **Telegram Bot API** при смене статуса и напоминаниях 24ч / 1ч

Правила доменов и ролей — в [`services/auth`](../auth/README.md). Контракт API — [`docs/api-contract.md`](../../docs/api-contract.md).

## Структура

| Файл | Назначение |
|------|------------|
| `app.py` | FastAPI-роуты |
| `main.py` | точка входа uvicorn |
| `db.py` | Postgres |
| `auth_utils.py` | JWT, bcrypt |
| `email_utils.py` / `email_verification.py` | SMTP и коды подтверждения |
| `telegram_utils.py` | sendMessage в Telegram |
| `booking_notify.py` | статусы + reminder loop |
| `captcha_utils.py` | Cloudflare Turnstile |

Сборка: context `./services` (подтягивает пакет `auth`).

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` | Postgres |
| `JWT_SECRET` | секрет JWT |
| `TELEGRAM_BOT_TOKEN` | токен бота для notify |
| `TELEGRAM_NOTIFY_ENABLED` | `true`/`false` (по умолчанию true) |
| `EMAIL_ENABLED`, `SMTP_*` | почта (коды + booking notify) |
| `TURNSTILE_SECRET_KEY` | captcha на web register |
| `BOOKING_REMINDER_POLL_SECONDS` | интервал poll напоминаний (по умолчанию 60) |
| `LINK_TOKEN_TTL_MINUTES` | TTL токена привязки Telegram |

## Запуск

```bash
# через compose (рекомендуется)
docker compose up -d --build backend

# health
curl http://localhost:8083/health
```

Локально без Docker: Postgres + `DATABASE_URL`, затем из `services/backend` (с `PYTHONPATH` на `services`):

```bash
python main.py
```

## Уведомления

Один путь доставки в `booking_notify._deliver`: email и/или Telegram по `users.email` / `users.telegram_id`.  
Напоминания пишут `reminder_24h_sent_at` / `reminder_1h_sent_at`, только если хотя бы один канал успешно отправил.

Отдельный Go-сервис `notification` слушает Kafka; backend сейчас **не публикует** события туда — продакшен-уведомления идут из backend напрямую.
