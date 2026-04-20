# Contributing to spbpu-booking

Благодарим вас за интерес к нашему проекту! Этот документ описывает процесс и правила разработки.

## 📋 Перед началом

### Обязательное чтение
1. 📖 [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - стратегия ветвления и коммитов
2. 📚 [docs/Requirements.md](docs/Requirements.md) - требования проекта
3. 🏗️ [docs/Architecture.md](services/notification-service/ARCHITECTURE.md) - архитектура сервисов

### Инструменты

Установите:
- Git 2.20+
- Docker & Docker Compose 1.28+
- Python 3.9+ (для Python сервисов)
- Go 1.21+ (для Notification Service)

## 🚀 Быстрый старт

### Первое время

```bash
# 1. Клонируем репозиторий
git clone https://github.com/your-org/spbpu-booking.git
cd spbpu-booking

# 2. Создаём .env файл из примера
cp .env.example .env

# 3. Запускаем проект
docker-compose up -d

# 4. Проверяем статус
docker-compose ps
```

### Перед каждой сессией разработки

```bash
# Получить последние изменения
git fetch origin
git checkout develop
git pull origin develop

# Создать feature ветвь
git checkout -b feature/service-name/what-you-do
```

## 🔧 Разработка

### Структура проекта

```
spbpu-booking/
├── services/           # Все микросервисы
│   ├── api-gateway/   # Точка входа (Python)
│   ├── auth-service/  # Аутентификация (Python)
│   ├── booking-service/  # Бронирования (Python)
│   ├── notification-service/  # Уведомления (Go)
│   ├── room-service/  # Управление комнатами (Python)
│   └── schedule-service/  # Расписания (Python)
├── database/          # SQL миграции
├── docs/             # Документация
└── docker-compose.yaml  # Оркестрация
```

### Разработка конкретного сервиса

#### Python сервисы

```bash
# Установить зависимости локально
cd services/booking-service
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt

# Запустить сервис локально (опционально)
python main.py

# Или через Docker (рекомендуется)
docker-compose up booking-service -d
```

#### Go сервис (Notification Service)

```bash
# Перейти в директорию
cd services/notification-service

# Скачать зависимости
go mod download

# Собрать локально
go build -o notification-service ./cmd/notification-service

# Или через Docker
docker-compose up notification-service -d
```

### Тестирование

```bash
# Запустить тесты для Python сервиса
cd services/booking-service
python -m pytest tests/

# Запустить тесты для Go сервиса
cd services/notification-service
go test ./...

# Все тесты (при наличии CI скрипта)
./scripts/run_tests.sh
```

### Логирование

```bash
# Просмотреть логи сервиса
docker-compose logs -f booking-service

# Последние 50 строк
docker-compose logs --tail=50 booking-service

# Все контейнеры
docker-compose logs -f
```

## 📝 Процесс PR

### Перед отправкой

```bash
# 1. Обновить из develop
git fetch origin
git rebase origin/develop

# 2. Проверить ваши коммиты
git log origin/develop..HEAD

# 3. Убедиться, что работает
docker-compose up -d
# [Тестирование]

# 4. Push
git push -u origin feature/your-feature
```

### Pull Request Template

При создании PR используйте этот шаблон:

```markdown
## Описание

Кратко опишите изменения.

## Мотивация

Почему это изменение необходимо? Какую проблему оно решает?

## Связанные Issue

Closes #123

## Тип изменения

- [ ] Bug fix (исправление без breaking changes)
- [ ] New feature (без breaking changes)
- [ ] Breaking change
- [ ] Documentation update

## Как это протестировано?

Опишите шаги для проверки.

## Чек-лист

- [ ] Мой код следует стилю проекта
- [ ] Я добавил тесты для новой функции
- [ ] Я обновил документацию
- [ ] Все тесты проходят локально
- [ ] Нет новых предупреждений
```

## ✅ Требования к качеству кода

### Обязательно

- ✅ Все коммиты должны следовать [Conventional Commits](https://www.conventionalcommits.org/)
- ✅ Минимум 1 code review от другого разработчика
- ✅ Все тесты должны проходить
- ✅ Не должно быть breaking changes без согласования

### Рекомендуется

- ✅ Добавить unit тесты для новой функции
- ✅ Добавить интеграционные тесты
- ✅ Обновить документацию
- ✅ Использовать type hints (Python), types (Go)

### Code Style

#### Python

```python
# Используем PEP 8
# Инструменты: black, flake8, mypy

# Примеры
def create_booking(user_id: int, room_id: int) -> Booking:
    """Create a new booking.
    
    Args:
        user_id: User identifier
        room_id: Room identifier
        
    Returns:
        Created booking object
    """
    pass
```

#### Go

```go
// Используем fmt и gofmt
// Инструменты: golangci-lint

// Примеры
func CreateBooking(userID int, roomID int) (*Booking, error) {
	// Implementation
	return nil, nil
}
```

## 🐛 Reporting Bugs

### Если нашли баг:

1. **Проверьте**, что баг не был уже заведён
2. **Опишите точно** как воспроизвести
3. **Включите** версии (Go, Python, Docker и т.д.)

Пример:

```
### Описание
Бронирование позволяет выбрать уже занятую комнату

### Как воспроизвести
1. Зайти на странице бронирования
2. Выбрать комнату 101
3. Выбрать время 10:00-11:00
4. Нажать забронировать

### Ожидаемое поведение
Ошибка "Комната занята"

### Текущее поведение
Бронирование создаётся успешно

### Окружение
- OS: Ubuntu 22.04
- Docker: 20.10
- Python: 3.9
```

## ❓ Questions?

- 📖 Читайте документацию в [docs/](docs/)
- 💬 Спросите в issue'е
- 📧 Свяжитесь с мейнтейнерами

---

**Спасибо за вклад! 🚀**
