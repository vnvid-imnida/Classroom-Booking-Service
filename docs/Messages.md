Вот схема полезной нагрузки (payload) для каждого типа сообщения в ваших exchanges.  
Она учитывает типы полей из таблиц, возможные сценарии изменений и минимизацию дублирования данных.

---

## 1. `booking.exchange`

### `booking.created`
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "booking.created",
  "timestamp": "2026-04-20T10:15:30Z",
  "version": 1,
  "data": {
    "booking_id": 12345,
    "user_id": 789,
    "room_id": 42,
    "time_start": "2026-04-25T09:00:00Z",
    "time_end": "2026-04-25T11:00:00Z",
    "status": "pending"
  },
  "metadata": {
    "source_service": "booking-api",
    "correlation_id": "req-abc-123"
  }
}
```

### `booking.updated`
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440001",
  "event_type": "booking.updated",
  "timestamp": "2026-04-20T10:17:45Z",
  "version": 1,
  "data": {
    "booking_id": 12345,
    "changed_fields": {
      "status": {
        "old": "pending",
        "new": "confirmed"
      },
      "time_end": {
        "old": "2026-04-25T11:00:00Z",
        "new": "2026-04-25T12:00:00Z"
      }
    },
    "current_full_state": null
  }
}
```
> *Поле `current_full_state` можно опустить или сделать опциональным, чтобы не дублировать все данные.*

### `booking.cancelled`
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440002",
  "event_type": "booking.cancelled",
  "timestamp": "2026-04-20T10:20:00Z",
  "version": 1,
  "data": {
    "booking_id": 12345,
    "user_id": 789,
    "room_id": 42,
    "cancelled_by": "user",
    "cancelled_at": "2026-04-20T10:20:00Z",
    "reason": "changed_plans"
  },
  "metadata": {
    "requires_audit": true
  }
}
```

---

## 2. `schedule.exchange`

### `schedule.synced`
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440010",
  "event_type": "schedule.synced",
  "timestamp": "2026-04-20T03:00:00Z",
  "version": 1,
  "data": {
    "source": "ruz",
    "sync_batch_id": "sync_20260420_030000",
    "rooms_affected": [42, 43, 101],
    "date_range": {
      "from": "2026-04-20",
      "to": "2026-05-20"
    },
    "changes_summary": {
      "inserted": 120,
      "updated": 35,
      "deleted": 2
    }
  }
}
```

### `schedule.conflict`
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440011",
  "event_type": "schedule.conflict",
  "timestamp": "2026-04-20T09:05:00Z",
  "version": 1,
  "data": {
    "conflict_type": "double_booking",
    "room_id": 42,
    "involved_booking_ids": [12345, 12350],
    "time_slot": {
      "start": "2026-04-25T09:00:00Z",
      "end": "2026-04-25T11:00:00Z"
    },
    "resolution": "manual_required"
  }
}
```

---

## 3. `room.exchange`

### `room.maintenance`
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440020",
  "event_type": "room.maintenance",
  "timestamp": "2026-04-20T08:00:00Z",
  "version": 1,
  "data": {
    "room_id": 42,
    "maintenance_status": "blocked",
    "start_time": "2026-04-20T08:00:00Z",
    "expected_end_time": "2026-04-22T18:00:00Z",
    "reason": "hvac_repair",
    "affected_future_bookings": [12345, 12346]
  }
}
```

### `room.updated`
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440021",
  "event_type": "room.updated",
  "timestamp": "2026-04-20T11:30:00Z",
  "version": 1,
  "data": {
    "room_id": 42,
    "changes": {
      "capacity": {
        "old": 50,
        "new": 55
      },
      "features": {
        "old": ["projector", "whiteboard"],
        "new": ["projector", "whiteboard", "air_conditioning"]
      }
    }
  }
}
```

---

## Общие рекомендации

- **`event_id`** — UUID для дедупликации на стороне consumer.
- **`timestamp`** — ISO 8601 (Zulu time).
- **`version`** — позволяет менять схему сообщений в будущем.
- **`metadata.correlation_id`** — связывает с исходным HTTP-запросом или внешним событием.
- Для больших объёмов (как `schedule_cache`) не передавайте `json_data` целиком, только мета-информацию об изменениях.
- Поле `data.current_full_state` в `booking.updated` передавайте только если consumer’ам это действительно нужно (обычно достаточно changed_fields).