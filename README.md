# spbpu-booking

Сервис бронирования аудиторий СПбПУ: веб, Telegram-бот, синхронизация с RUZ, уведомления.

## Обязательные документы

1. [GIT_WORKFLOW.md](GIT_WORKFLOW.md) — ветки, коммиты, Pull Request  
2. [CONTRIBUTING.md](CONTRIBUTING.md) — ежедневный процесс  
3. [CHANGELOG.md](CHANGELOG.md) — история релизов  

Дополнительно: [docs/api-contract.md](docs/api-contract.md), [docs/BOT_LOGIN.md](docs/BOT_LOGIN.md).

## Быстрый старт

```bash
git clone <repo-url>
cd spbpu-booking

cp .env.example .env   # заполнить TELEGRAM_BOT_TOKEN, SMTP_*, JWT_SECRET, …

git checkout develop
git pull origin develop
git checkout -b feature/<service>/<task>

docker compose up -d --build
```

Полезные URL после подъёма:

| Сервис | URL |
|--------|-----|
| Backend API | http://localhost:8083/health |
| Parser (RUZ) | http://localhost:8082/health |
| Notification | http://localhost:8084/health |
| Telegram bot health | http://localhost:8090/health |
| Kafka UI | http://localhost:8080 |

## Сервисы

| Путь | Описание | README |
|------|----------|--------|
| `services/backend` | REST API, email + Telegram notify | [README](services/backend/README.md) |
| `services/telegram-frontend` | Telegram-бот (aiogram) | [README](services/telegram-frontend/README.md) |
| `services/parser` | Sync расписания RUZ → bookings | [README](services/parser/README.md) |
| `services/notification` | Kafka → уведомления (Go) | [README](services/notification/README.md) |
| `services/message-generator` | Тестовый Kafka-продюсер | [README](services/message-generator/README.md) |
| `services/auth` | Общие правила доменов/ролей | [README](services/auth/README.md) |
| `services/frontend` | Web UI (React) | [README](services/frontend/README.md) |

Инфра в `docker-compose.yaml`: Postgres, Redis, Kafka, ZooKeeper.

## Базовые команды

```bash
docker compose up -d
docker compose ps
docker compose logs -f backend
docker compose up -d --build backend telegram parser
```

Тестовый генератор Kafka (опционально):

```bash
docker compose --profile generator up --build generator
```

## Структура репозитория

```text
services/    # микросервисы и shared auth
docs/        # API-контракт, гайды бота
.github/     # шаблоны issue / PR
scripts/     # локальные скрипты запуска
```

Организационные правила — в трёх документах в начале README. Если процесс меняется, сначала документация, потом код.
