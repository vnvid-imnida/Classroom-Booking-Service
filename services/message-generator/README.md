# Message generator (`services/message-generator`)

Тестовый продюсер Kafka: шлёт фейковые события бронирований/расписания в топики notification-сервиса.

Compose-сервис: `generator` · **профиль** `generator` (по умолчанию не стартует).

## Назначение

- Проверка consumer'а `notification-service` без реального backend
- Демо пайплайна Kafka → notify

**Не для продакшена.** Реальные статусные уведомления идут из backend.

## События

Генерирует сообщения по схеме топиков (`booking.created`, `booking.updated`, `booking.cancelled`, и др.) с тестовыми `user_id` / `telegram_id` / слотами между парами.

## Запуск

```bash
# вместе с Kafka + notification
docker compose --profile generator up --build generator

# или разово
docker compose --profile generator run --rm generator
```

Env: `KAFKA_BOOTSTRAP_SERVERS` (в compose: `kafka:9092`).

Перед прогоном убедитесь, что `notification-service` запущен и при необходимости `TELEGRAM_ENABLED=true` с валидным токеном.
