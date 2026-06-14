# Вход в Telegram-боте (без Web App)

Правила auth (домены, роли, тексты) — пакет `services/auth/`. Бот вызывает те же API, что и сайт (`/api/v1/auth/login`, `/register`).

## Схема

1. Регистрация: на сайте (`FRONTEND_URL/register`) или в боте (кнопка «Регистрация» при неизвестном email → email → ФИО → пароль → `POST /api/v1/auth/register` + вход).
2. В боте: `/start` — сразу запрос email; `/login` — тот же FSM (email → пароль).
3. Неизвестный email: сообщение «Пользователь с таким email не найден» и inline-кнопка «Регистрация» (не «неверный пароль»).
4. Бот вызывает `POST /api/v1/auth/login` с заголовками `X-Telegram-Id` и опционально `X-Telegram-Username`.
5. Backend привязывает `telegram_id` к веб-аккаунту и возвращает JWT.
6. Бот показывает главное меню; `AuthMiddleware` пропускает запросы с привязанным Telegram.

## Опциональная привязка по коду

В личном кабинете на сайте можно получить одноразовый токен и отправить в боте:

```
/start link_<токен>
```

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `FRONTEND_URL` | URL фронтенда для подсказки регистрации (локально: `http://localhost:5173`) |
| `BACKEND_URL` | API для бота (по умолчанию `http://127.0.0.1:8083`) |
| `TELEGRAM_BOT_TOKEN` | Токен @BotFather |

## Локальный запуск (рекомендуется)

**Не запускайте бота через Docker**, если разрабатываете локально: образ `telegram` в `docker-compose.yaml` (профиль `docker-telegram`) может быть старым и снова показывать Web App.

```powershell
# Терминал 1 — backend
.\scripts\start-backend.ps1

# Терминал 2 — frontend (регистрация на сайте)
.\scripts\start-frontend.ps1

# Терминал 3 — бот (только так)
cd services\telegram-frontend
python main.py
```

Перед запуском остановите контейнер, если он уже крутится:

```powershell
docker compose --profile docker-telegram stop telegram
```

В `.env` (корень репозитория):

```
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://127.0.0.1:8083
TELEGRAM_BOT_TOKEN=...
```

## Если всё ещё видна кнопка Web App

Код больше не отправляет `web_app` в клавиатуре. Кнопка могла остаться из **кэша Telegram**:

| Источник | Что делать |
|----------|------------|
| **Menu button** (синяя кнопка «Открыть» у поля ввода) | При старте бот вызывает `set_chat_menu_button(MenuButtonDefault())`. Перезапустите `python main.py`. |
| **Старая reply-клавиатура** в чате | Бот шлёт `ReplyKeyboardRemove`. Удалите чат с ботом и начните заново **или** отправьте `/start` дважды подряд. |
| **Docker `telegram` сервис** | Остановите контейнер; запускайте только `python main.py` из `services/telegram-frontend`. |

## Проверка API (curl)

```powershell
$headers = @{ "X-Telegram-Id" = "123456789"; "Content-Type" = "application/json" }
$body = @{ email = "user@example.com"; password = "secret" } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8083/api/v1/auth/login" -Headers $headers -Body $body
```

В ответе `user.telegram_id` должен совпасть с заголовком.

## Команды бота

| Команда | Действие |
|---------|----------|
| `/start` | Привязан: статус «вы авторизованы» + меню; иначе приветствие → email → пароль |
| `/login` | Выход (отвязка Telegram) и вход заново с email |
| `/logout` | Отвязка Telegram; далее `/start` |
| `/help` | Справка (URL регистрации только здесь) |
