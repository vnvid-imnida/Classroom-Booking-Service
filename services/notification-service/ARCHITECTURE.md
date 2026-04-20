# Notification Service Architecture

## 📦 Компоненты

### Язык: Golang (Go)

Выбран Go за счет:
- ⚡ Высокая производительность
- 🔄 Встроенная поддержка асинхронных операций (goroutines)
- 📦 Статический бинарник (легко деплоить в контейнеры)
- 🎯 Идеально для микросервисов с высокой нагрузкой

---

## 🏗️ Структура проекта

```
services/notification-service/
├── main.go                 # Точка входа, HTTP API
├── config.go              # Загрузка конфигурации из env
├── database.go            # Работа с PostgreSQL
├── kafka.go               # Консьюмер для Kafka
├── notification.go        # Отправка уведомлений
├── go.mod                 # Dependencies
├── go.sum                 # Dependency checksums
└── Dockerfile             # Multi-stage Docker build
```

---

## 🔄 Жизненный цикл обработки сообщений

```
┌─────────────────────────────────────────────┐
│  KAFKA CONSUMER (kafka.go)                  │
│  - Слушает топики: booking.*, room.*, etc. │
│  - Читает сообщения из Kafka                │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  MESSAGE PARSING                            │
│  - Десериализация JSON                      │
│  - Валидация структуры                      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  EVENT ROUTING (kafka.go - processEvent)    │
│  - Определение типа события                 │
│  - Выбор обработчика                        │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴───────┬─────────────┐
       │               │             │
       ▼               ▼             ▼
   ┌────────┐     ┌───────┐     ┌─────────┐
   │Booking │     │Room   │     │Schedule │
   │Events  │     │Events │     │Events   │
   └────────┘     └───────┘     └─────────┘
       │               │             │
       └───────────────┴─────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  GET USER INFO (database.go)                │
│  - По booking_id получить user_id           │
│  - Получить email и telegram_id             │
│  - Загрузить предпочтения уведомлений       │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  FORMAT MESSAGE (notification.go)           │
│  - Форматирование текста для Telegram       │
│  - Подготовка HTML для Email                │
└──────────────┬──────────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
   ┌────────┐    ┌────────┐
   │Telegram│    │Email   │
   │Send    │    │Send    │
   └────┬───┘    └────┬───┘
        │             │
        └──────┬──────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  SAVE TO DB (database.go)                   │
│  - Сохранить уведомление                    │
│  - Обновить статус (sent/failed)            │
└─────────────────────────────────────────────┘
```

---

## 📋 Модули и их функции

### 1. main.go
**Отвечает за:**
- Инициализацию приложения
- Запуск HTTP сервера
- Управление жизненным циклом сервиса

**Endpoints:**
```
GET /health   - Проверка здоровья (для healthcheck)
GET /metrics  - Статистика обработанных сообщений
GET /status   - Детальный статус всех компонентов
```

### 2. config.go
**Отвечает за:**
- Загрузку переменных окружения
- Валидацию конфигурации
- Предоставление доступа к параметрам

**Поддерживаемые env переменные:**
```
SERVICE_NAME              - Имя сервиса
SERVICE_PORT              - Порт для HTTP сервера
DEBUG                     - Режим отладки
DATABASE_URL              - Строка подключения к PostgreSQL
KAFKA_BOOTSTRAP_SERVERS   - Адреса Kafka брокеров
KAFKA_GROUP_ID            - ID группы консьюмера
KAFKA_TOPICS              - Список топиков для подписки
TELEGRAM_BOT_TOKEN        - Токен Telegram бота
TELEGRAM_CHAT_ID          - Chat ID для Telegram
TELEGRAM_ENABLED          - Включить/отключить Telegram
SMTP_HOST, PORT, USER...  - Email параметры
EMAIL_ENABLED             - Включить/отключить Email
```

### 3. database.go
**Отвечает за:**
- Инициализацию пула подключений PostgreSQL
- CRUD операции с таблицей notifications
- Получение данных пользователя (email, telegram_id)

**Функции:**
```go
InitDB()                      - Инициализация пула БД
CloseDB()                     - Закрытие пула БД
SaveNotification()            - Сохранить уведомление
UpdateNotificationStatus()    - Обновить статус
GetUserByBookingID()          - Получить пользователя по бронированию
GetUserEmail()                - Получить email пользователя
GetUserTelegramID()           - Получить Telegram ID
```

**Таблица notifications:**
```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    booking_id INTEGER,
    message TEXT NOT NULL,
    notification_type VARCHAR(50),
    event_id VARCHAR(100) UNIQUE,
    status VARCHAR(20),      -- pending, sent, failed
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    sent_at TIMESTAMP,
    failed_reason TEXT
);
```

### 4. kafka.go
**Отвечает за:**
- Подключение к Kafka
- Чтение сообщений из топиков
- Маршрутизация событий
- Управление смещениями (offsets)
- Коммитирование обработанных сообщений

**Основной класс:**
```go
type KafkaConsumerManager struct {
    reader          *kafka.Reader
    cfg             Config
    notificationMgr *NotificationManager
    isRunning       atomic.Bool
    processedCount  atomic.Int64
    failedCount     atomic.Int64
}
```

**Методы:**
```go
Start()          - Запустить консьюмер
Stop()           - Остановить консьюмер
consume()        - Основной цикл обработки
handleMessage()  - Обработка одного сообщения
processEvent()   - Маршрутизация события
GetMetrics()     - Получить метрики
```

### 5. notification.go
**Отвечает за:**
- Управление отправкой уведомлений
- Интеграция с Telegram Bot API
- Интеграция с SMTP для Email
- Форматирование сообщений

**Основной класс:**
```go
type NotificationManager struct {
    cfg    Config
    dialer *gomail.Dialer
}
```

**Методы:**
```go
SendNotification()      - Отправить уведомление всеми каналами
sendTelegram()          - Отправить в Telegram
sendEmail()             - Отправить Email
FormatBookingMessage()  - Форматировать сообщение о бронировании
FormatRoomMessage()     - Форматировать сообщение о комнате
FormatScheduleMessage() - Форматировать сообщение о расписании
```

---

## 🔐 Обработка ошибок

```
Ошибка БД
    └─→ Логирование + Обновление статуса: failed
    └─→ Сохранение причины ошибки
    └─→ Retry: до 3 попыток

Ошибка Telegram
    └─→ Логирование + Попытка Email
    └─→ Обновление статуса: failed
    └─→ Запись текста ошибки

Ошибка Email
    └─→ Логирование + Продолжение работы
    └─→ Обновление статуса: sent (если успел Telegram)
    └─→ Запись текста ошибки
```

---

## 📊 Метрики

Сервис отслеживает:
- `processed_messages` - Всего обработано сообщений
- `failed_messages` - Ошибок при обработке
- `status` - Текущий статус (true = работает)

Эти метрики доступны через:
```bash
GET /metrics
```

---

## 🚀 Производительность

### Ожидаемые характеристики:

- **Throughput:** 1000+ сообщений/сек
- **Latency:** < 100ms от Kafka до отправки
- **Memory:** ~50-100MB при среднем потреблении
- **CPU:** < 10% на одном ядре при обычной нагрузке

### Оптимизации:

1. **Goroutines:** Асинхронная отправка Telegram и Email
2. **Connection pooling:** Переиспользование соединений с БД
3. **Batch commits:** Коммит смещений пакетами
4. **Timeouts:** Использование контекстов для управления таймаутами

---

## 🔍 Мониторинг

### Важные метрики для мониторинга:

1. **Kafka:**
   - Lag (отставание) консьюмера
   - Количество сообщений в топиках
   - Статус брокеров

2. **Приложение:**
   - HTTP response time
   - Процент ошибок при обработке
   - Использование памяти и CPU

3. **База данных:**
   - Количество активных соединений
   - Время выполнения запросов
   - Размер таблицы notifications

### Команды для мониторинга:

```bash
# Мониторинг в реальном времени
docker stats notification-service

# Логи в реальном времени
docker-compose logs -f notification-service

# Статус контейнеров
docker-compose ps

# Использование памяти
docker container stats --no-stream notification-service
```

---

## 🔧 Отладка

### Включить режим отладки:

```bash
# В .env файле
DEBUG=true

# Или через env
docker-compose up -e DEBUG=true
```

### Полезные команды:

```bash
# Проверка конфигурации сервиса
docker-compose exec notification-service env

# Проверка подключения к Kafka
docker-compose exec kafka kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# Проверка подключения к БД
docker-compose exec postgres psql -U notification_user -d notification_db -c "SELECT 1"

# Проверка свежести обработки
docker-compose exec kafka kafka-consumer-groups.sh --bootstrap-server kafka:9092 --group notification-service-group --describe
```

---

## 📈 Масштабирование

### Горизонтальное масштабирование:

Можно запустить несколько копий Notification Service:

```yaml
notification-service-1:
  # ... конфигурация

notification-service-2:
  # ... конфигурация (другой KAFKA_GROUP_ID)

notification-service-3:
  # ... конфигурация (другой KAFKA_GROUP_ID)
```

Kafka автоматически распределит сообщения между инстансами.

### Вертикальное масштабирование:

```bash
# Увеличить количество воркеров в consume()
go func() kcm.handleMessage(msg) }()

# Увеличить размер пула БД
config.MaxConns = 50
config.MinConns = 20
```

---

## 🎯 Future Improvements

- [ ] Добавить Redis кэширование для user data
- [ ] Реализовать retry queue через Kafka
- [ ] Добавить SMS отправку через Twilio
- [ ] Реализовать в-приложение уведомления (WebSocket)
- [ ] Добавить метрики Prometheus
- [ ] Добавить трейсинг через Jaeger
- [ ] Реализовать шифрование чувствительных данных
- [ ] Добавить rate limiting для API
