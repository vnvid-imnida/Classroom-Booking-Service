# Telegram bot (`services/telegram-frontend`)

Aiogram-бот для бронирования: вход, заявки, кабинет, модерация. Вся бизнес-логика — через backend API.

Порт health: **8090** · Compose-сервис: `telegram`

Подробнее про логин: [`docs/BOT_LOGIN.md`](../../docs/BOT_LOGIN.md).

## Возможности

- Регистрация / вход (те же `/api/v1/auth/*`, что у сайта)
- Привязка Telegram по email+пароль или `/start link_<token>`
- Поиск свободных аудиторий и подача заявки
- Личный кабинет: активные / архивные, отмена
- Модерация заявок (роли admin / dispatcher)
- Без воскресений (как на сайте)

## Структура

```text
main.py                 # бот + /health
bot/config.py           # env
bot/api/client.py       # HTTP к backend
bot/handlers/           # booking, cabinet, moderation, common
bot/middleware/auth.py  # проверка привязки telegram_id
bot/keyboards.py
bot/states.py           # FSM
```

Сборка: context `./services` (доступ к пакету `auth` для доменов/сообщений).

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | токен @BotFather (**обязателен**) |
| `BACKEND_URL` | API (в compose: `http://backend:8083`) |
| `FRONTEND_URL` | ссылка на сайт для подсказок регистрации |
| `SERVICE_PORT` / health | по умолчанию `8090` |

## Запуск

```bash
# Docker
docker compose up -d --build telegram

# Локально (удобно при разработке бота)
# Терминал 1: backend уже запущен
# Терминал 2:
cd services/telegram-frontend
python main.py
```

Команды бота: `/start`, `/login`, `/logout`, `/help`.

## Замечания

- Прокси-переменные (`HTTP_PROXY` и т.п.) снимаются при старте — иначе ломается `api.telegram.org` и localhost.
- Уведомления о статусе заявки шлёт **backend** (`telegram_utils`), не сам бот.
