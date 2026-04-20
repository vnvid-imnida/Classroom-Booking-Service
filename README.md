# 🏢 spbpu-booking - Микросервисное приложение для системы бронирования

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/status-In%20Development-yellow)

Распределённая система управления бронированием комнат и помещений для СПбПУ (Санкт-Петербургский политехнический университет).

## 📋 Содержание

- [Особенности](#особенности)
- [Архитектура](#архитектура)
- [Быстрый старт](#быстрый-старт)
- [Структура проекта](#структура-проекта)
- [Разработка](#разработка)
- [Git управление](#git-управление)
- [Документация](#документация)
- [Contributing](#contributing)

## ✨ Особенности

- 🏗️ **Микросервисная архитектура** - Независимо масштабируемые сервисы
- 🔄 **Асинхронная обработка** - Kafka для обработки сообщений
- 🐘 **PostgreSQL** - Надёжное хранилище данных
- 🚀 **Go & Python** - Оптимальный язык для каждого сервиса
- 🐳 **Docker** - Контейнеризация и оркестрация
- ⚡ **Redis** - Кеширование и быстрый доступ
- 🔐 **JWT Authentication** - Безопасная аутентификация
- 📊 **Kafka UI** - Мониторинг сообщений
- 🧪 **Unit & Integration тесты** - Высокое качество кода

## 🏗️ Архитектура

```
┌─────────────┐
│  Frontend   │
└──────┬──────┘
       │
       v
┌─────────────────────────────────────────────────┐
│         API Gateway (Python)                    │
│  - Маршрутизация запросов                       │
│  - Rate limiting                                 │
│  - CORS handling                                │
└──┬────────┬────────┬────────┬────────┬────────┘
   │        │        │        │        │
   v        v        v        v        v
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│Auth  │ │Room  │ │Book  │ │Sch   │ │Notif │
│Svc   │ │Svc   │ │Svc   │ │Svc   │ │Svc   │
└──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
   │        │        │        │        │
   └────────┴────────┴────────┴────────┘
         (Kafka Message Broker)
         
┌─────────────────────────────────────┐
│      Infrastructure                 │
├─────────────┬───────────┬───────────┤
│ PostgreSQL  │  Redis    │   Kafka   │
│             │           │  Zookeeper│
└─────────────┴───────────┴───────────┘
```

### Сервисы

| Сервис | Язык | Порт | Описание |
|--------|------|------|---------|
| **API Gateway** | Python | 3000 | Точка входа, маршрутизация |
| **Auth Service** | Python | 8085 | Аутентификация, JWT валидация |
| **Room Service** | Python | 8081 | Управление комнатами |
| **Booking Service** | Python | 8083 | Управление бронированиями |
| **Schedule Service** | Python | 8082 | Синхронизация расписаний |
| **Notification Service** | Go | 8084 | Отправка уведомлений |

## 🚀 Быстрый старт

### Требования

- Docker 20.10+
- Docker Compose 1.28+
- Git 2.20+
- Python 3.9+ (для локальной разработки)
- Go 1.21+ (для локальной разработки)

### Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/your-org/spbpu-booking.git
cd spbpu-booking

# 2. Создать .env файл
cp .env.example .env
# Отредактируйте .env при необходимости

# 3. Запустить Docker Compose
docker-compose up -d

# 4. Проверить статус сервисов
docker-compose ps

# 5. Просмотреть логи
docker-compose logs -f
```

### Проверка установки

```bash
# API Gateway
curl http://localhost:3000/health

# Kafka UI
open http://localhost:8080

# PostgreSQL
psql -h localhost -U notification_user -d notification_db
```

## 📁 Структура проекта

```
spbpu-booking/
├── .github/                        # GitHub конфигурация
│   ├── ISSUE_TEMPLATE/            # Шаблоны для issues
│   └── pull_request_template.md    # Шаблон PR
├── services/                       # Все микросервисы
│   ├── api-gateway/               # Главная точка входа (Python)
│   ├── auth-service/              # Аутентификация (Python)
│   ├── booking-service/           # Бронирования (Python)
│   ├── notification-service/      # Уведомления (Go)
│   ├── room-service/              # Управление комнатами (Python)
│   └── schedule-service/          # Расписания (Python)
├── database/                       # Database структура
│   ├── init.sql                   # Инициализация БД
│   └── migrations/                # SQL миграции
├── message-generator/             # Генератор тестовых сообщений
├── docs/                          # Документация
│   ├── Requirements.md            # Требования
│   ├── Database.md                # Схема БД
│   ├── Messages.md                # Формат сообщений
│   └── Topology.md                # Топология сети
├── docker-compose.yaml            # Docker оркестрация
├── .gitignore                     # Git игнорирование
├── .gitattributes                 # Правила для файлов
├── .editorconfig                  # Форматирование кода
├── GIT_WORKFLOW.md                # Git стратегия (ЧИТАТЬ!)
├── CONTRIBUTING.md                # Contributing guide (ЧИТАТЬ!)
├── CHANGELOG.md                   # История версий
└── README.md                      # Этот файл
```

## 🔧 Разработка

### Локальная разработка

#### Python сервисы

```bash
# Войти в директорию сервиса
cd services/booking-service

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить тесты
python -m pytest tests/

# Запустить сервис локально
python main.py
```

#### Go сервис (Notification Service)

```bash
# Войти в директорию
cd services/notification-service

# Скачать зависимости
go mod download

# Запустить тесты
go test ./...

# Собрать локально
go build -o notification-service ./cmd/notification-service

# Запустить
./notification-service
```

### Тестирование

```bash
# Тесты в контейнере для Python
docker-compose exec booking-service python -m pytest

# Тесты для Go
docker-compose exec notification-service go test ./...

# Все логи
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f booking-service
```

### Отладка

```bash
# Зайти в контейнер
docker-compose exec booking-service bash

# Проверить переменные окружения
docker-compose exec booking-service env | grep DATABASE

# Проверить сетевое подключение
docker-compose exec booking-service ping postgres
```

## 📝 Git управление

**⚠️ ВАЖНО: Перед началом разработки прочитайте [GIT_WORKFLOW.md](GIT_WORKFLOW.md)**

### Быстрые команды

```bash
# Создать feature ветвь
git checkout develop
git pull origin develop
git checkout -b feature/service-name/description

# Коммитить в соответствии с Conventional Commits
git commit -m "feat(booking): add cancellation endpoint"

# Push и создать PR
git push -u origin feature/service-name/description
```

### Соглашения о коммитах

```
feat(scope): short description      # ✨ Новая функция
fix(scope): short description       # 🐛 Исправление
docs: short description             # 📚 Документация
test(scope): short description      # ✅ Тесты
refactor(scope): short description  # ♻️ Рефакторинг
chore: short description            # 🔧 Конфигурация
```

### Ветвление (Git Flow)

- `main` - Production releases (protected)
- `develop` - Integration branch (protected)
- `feature/*` - Новые функции из develop
- `bugfix/*` - Исправления из develop
- `hotfix/*` - Критичные исправления из main
- `release/*` - Подготовка к релизу

Подробнее в [GIT_WORKFLOW.md](GIT_WORKFLOW.md)

## 📚 Документация

- [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - **Стратегия Git ветвления и коммитов**
- [CONTRIBUTING.md](CONTRIBUTING.md) - **Руководство для разработчиков**
- [docs/Requirements.md](docs/Requirements.md) - Требования к системе
- [docs/Architecture.md](services/notification-service/ARCHITECTURE.md) - Архитектура сервисов
- [docs/Database.md](docs/Database.md) - Схема базы данных
- [docs/Messages.md](docs/Messages.md) - Формат сообщений Kafka
- [docs/Topology.md](docs/Topology.md) - Топология и порты сервисов

## 🤝 Contributing

Мы приветствуем вклады! Пожалуйста:

1. Прочитайте [CONTRIBUTING.md](CONTRIBUTING.md)
2. Следуйте [GIT_WORKFLOW.md](GIT_WORKFLOW.md)
3. Создайте feature ветвь
4. Коммитьте с описанием (Conventional Commits)
5. Отправьте Pull Request

### Процесс PR

1. Fork репозиторий
2. Создайте feature ветвь (`git checkout -b feature/amazing-feature`)
3. Коммитьте изменения (`git commit -m 'feat(scope): add amazing feature'`)
4. Push в ветвь (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

**Требования к PR:**
- ✅ Все тесты проходят
- ✅ Код отформатирован правильно
- ✅ Включена документация
- ✅ Минимум 1 review
- ✅ Нет конфликтов с develop

## 📋 Процесс разработки

```
1. Update develop
   git fetch origin && git checkout develop && git pull

2. Create feature branch
   git checkout -b feature/service-name/feature-description

3. Make changes & commit
   git commit -m "feat(service): description"

4. Push & create PR
   git push -u origin feature/service-name/feature-description

5. Code review & merge
   (Reviewer approves and merges to develop)

6. Deploy
   (CI/CD pipeline handles deployment)
```

## 🐛 Reporting Issues

Используйте GitHub Issues для:
- 🐛 Bug reports - используйте шаблон "Bug Report"
- ✨ Feature requests - используйте шаблон "Feature Request"
- 📚 Documentation - используйте шаблон "Documentation"

## 📦 Зависимости

### Python
- FastAPI - Web framework
- Kafka-python - Kafka client
- SQLAlchemy - ORM
- Pydantic - Data validation

### Go
- gin-gonic/gin - Web framework
- confluentinc/confluent-kafka-go - Kafka client
- lib/pq - PostgreSQL driver

### Infrastructure
- PostgreSQL 15
- Redis 7
- Kafka 7.5
- Zookeeper 7.5

## 🔐 Security

- JWT для аутентификации
- CORS настройки
- Rate limiting
- SQL injection protection
- Environment-based configuration (не коммитим secrets)

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 👥 Контакты

- 📧 Email: dev@spbpu.ru
- 💬 Issues: GitHub Issues
- 📖 Docs: [docs/](docs/)

---

**Последнее обновление:** 2024  
**Статус:** In Development 🚀

