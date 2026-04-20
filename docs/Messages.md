# Kafka Messages

Актуальные события для notification-service.

## Общий формат

```json
{
  "event_id": "uuid",
  "event_type": "booking.created",
  "timestamp": "2026-04-20T10:15:30Z",
  "version": 1,
  "data": {},
  "metadata": {
    "source_service": "booking-service",
    "correlation_id": "req-123"
  }
}
```

## Поддерживаемые event_type

- `booking.created`
- `booking.updated`
- `booking.cancelled`
- `schedule.synced`
- `schedule.conflict`
- `user.created`

`room.*` считаются legacy-событиями и не являются основным сценарием для ВУЗ-расписания.

## Минимальные payload-поля по типам

### booking.created

```json
{
  "data": {
    "booking_id": 12345,
    "user_id": 789,
    "room_id": 42,
    "time_start": "2026-04-25T09:00:00Z",
    "time_end": "2026-04-25T11:00:00Z",
    "status": "pending",
    "source": "schedule_gap_recommendation"
  }
}
```

### booking.updated

```json
{
  "data": {
    "booking_id": 12345,
    "user_id": 789,
    "room_id": 42,
    "changed_fields": {
      "time_start": { "old": "2026-04-25T09:00:00Z", "new": "2026-04-25T10:40:00Z" },
      "time_end": { "old": "2026-04-25T11:00:00Z", "new": "2026-04-25T12:10:00Z" },
      "status": { "old": "confirmed", "new": "rescheduled" }
    }
  }
}
```

### booking.cancelled

```json
{
  "data": {
    "booking_id": 12345,
    "user_id": 789,
    "room_id": 42,
    "cancelled_by": "schedule-service",
    "reason": "class_schedule_changed"
  }
}
```

### schedule.synced

```json
{
  "data": {
    "source": "ruz",
    "sync_batch_id": "sync_20260420_030000",
    "rooms_affected": [42, 43],
    "date_range": {
      "from": "2026-04-20",
      "to": "2026-05-04"
    },
    "changes_summary": {
      "lessons_inserted": 32,
      "lessons_updated": 11,
      "lessons_deleted": 2,
      "booking_conflicts_detected": 3
    }
  }
}
```

### schedule.conflict

```json
{
  "data": {
    "conflict_type": "class_overlap",
    "room_id": 42,
    "involved_booking_ids": [12345],
    "booking_time_slot": {
      "start": "2026-04-25T10:40:00Z",
      "end": "2026-04-25T12:10:00Z"
    },
    "lesson_time_slot": {
      "start": "2026-04-25T11:00:00Z",
      "end": "2026-04-25T12:30:00Z"
    },
    "resolution": "auto_cancelled"
  }
}
```

### user.created

```json
{
  "data": {
    "telegram_id": 1333800382,
    "username": "Koshsky"
  }
}
```

## Поведение notification-service

- Для `booking.*`: точечная отправка конкретному пользователю из поля `user_id`, создается запись `notifications`, выполняется Telegram-отправка, затем статус `sent` или `failed`.
- Для `schedule.*`: массовая рассылка всем пользователям из таблицы `users`, создаются записи `notifications`, выполняется Telegram-отправка, затем статус `sent` или `failed`.
- Для legacy `room.*`: массовая рассылка всем пользователям из таблицы `users`.
- Для `user.created`: только upsert в `users` по `telegram_id`, без рассылки и без записи в `notifications`.

## Правила совместимости

1. `event_id` обязателен и уникален (UUID).
2. `timestamp` в ISO 8601 UTC.
3. `version` обязателен.
4. Новые поля добавлять обратно-совместимо.
5. Для всех `booking.*` событий поле `data.user_id` обязательно.