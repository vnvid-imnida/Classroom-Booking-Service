# Parser (`services/parser`)

Синхронизация расписания СПбПУ (RUZ API) в таблицу `bookings` с `source=RUZ`, чтобы свободные слоты учитывали пары.

Порт: **8082** · Compose-сервис: `parser`

## Как работает

1. Тянет корпуса / аудитории / занятия из `https://ruz.spbstu.ru/api/v1/ruz`.
2. Сопоставляет аудитории с локальными `rooms` (корпус + номер).
3. Upsert броней `source=RUZ` на окно `RUZ_SYNC_WEEKS` недель вперёд.
4. Периодический sync в фоне + ручной trigger по HTTP.

## Структура

| Файл | Назначение |
|------|------------|
| `main.py` | FastAPI: `/health`, `/sync` |
| `sync.py` | оркестрация sync |
| `ruz_client.py` | HTTP-клиент RUZ |
| `db.py` | Postgres upsert |
| `config.py` | env (+ `.env` с корня репо) |

## HTTP

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | статус + last sync |
| GET | `/sync` | running / last result |
| POST | `/sync` | запуск в фоне (`{"weeks": 3}` опционально) |
| POST | `/sync/run` | sync в запросе (для отладки, может идти минуты) |

`409`, если sync уже идёт.

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DATABASE_URL` | local postgres | БД booking |
| `RUZ_BASE_URL` | `…/api/v1/ruz` | база RUZ |
| `RUZ_SYNC_WEEKS` | `3` | горизонт sync |
| `RUZ_SYNC_INTERVAL_SECONDS` | `3600` | период; `≤0` — только ручной |
| `RUZ_REQUEST_DELAY_SEC` | `0.2` | пауза между запросами к RUZ |

## Запуск

```bash
docker compose up -d --build parser

curl http://localhost:8082/health
curl -X POST http://localhost:8082/sync
```
