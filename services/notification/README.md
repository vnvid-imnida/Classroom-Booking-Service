# Notification service (`services/notification`)

Go-сервис: consumer Kafka → сохранение уведомления в БД → опционально Telegram.

Порт: **8084** · Compose-сервис: `notification-service`

## Статус в проекте

Слушает топики вроде `booking.created`, `booking.updated`, `booking.cancelled`, `schedule.synced`, `schedule.conflict`.

**Продакшен-путь уведомлений сейчас другой:** backend шлёт email/Telegram напрямую (`booking_notify` + `telegram_utils`).  
Этот сервис полезен для Kafka-пайплайна и нагрузочных/интеграционных тестов (см. [`message-generator`](../message-generator/README.md)).

## Структура

```text
cmd/notification-service/main.go
internal/config/
internal/kafka/          # consumer
internal/notification/   # Manager + Telegram send
internal/database/
internal/models/
```

## HTTP

| Путь | Описание |
|------|----------|
| `GET /health` | liveness |
| `GET /status` | состояние consumer |
| `GET /metrics` | простые метрики |

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` | Postgres |
| `KAFKA_BOOTSTRAP_SERVERS` | брокеры |
| `KAFKA_GROUP_ID` | consumer group |
| `KAFKA_TOPICS` | список топиков через запятую |
| `TELEGRAM_BOT_TOKEN` | токен бота |
| `TELEGRAM_CHAT_ID` | fallback chat (broadcast / debug) |
| `TELEGRAM_ENABLED` | включить отправку в TG |
| `REDIS_URL` | Redis |
| `MAX_RETRIES`, `MESSAGE_PROCESSING_TIMEOUT` | устойчивость обработки |

## Запуск

```bash
docker compose up -d --build notification-service

curl http://localhost:8084/health
```

Kafka UI (если поднят): http://localhost:8080
