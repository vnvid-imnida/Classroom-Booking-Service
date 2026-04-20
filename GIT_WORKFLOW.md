# Git Workflow Guide для spbpu-booking

Этот документ описывает рекомендуемую стратегию работы с Git для микросервисного приложения.

## 📋 Таблица содержания

1. [Стратегия ветвления](#стратегия-ветвления)
2. [Соглашения о коммитах](#соглашения-о-коммитах)
3. [Процесс разработки](#процесс-разработки)
4. [Pull Request процесс](#pull-request-процесс)
5. [Релизы](#релизы)

---

## Стратегия ветвления

Мы используем **Git Flow** (модифицированный) для управления ветвлением:

### Основные ветви

#### `main` (Production)
- ✅ **Защищена от прямых коммитов**
- 📍 Содержит только стабильные релизы
- 🏷️ Каждый коммит помечается тегом версии: `v1.0.0`, `v1.1.0` и т.д.
- 🔄 Обновляется только через merge из `release/*` ветвей

```
main ← release/v1.0.0 ← feature/... ← develop
```

#### `develop` (Development)
- 📦 Ветвь интеграции всех функций
- ✅ Должна быть **всегда деплояемой**
- 🔄 Обновляется через Pull Request'ы из feature ветвей
- 🚀 Используется для развертывания на staging

### Вспомогательные ветви

#### Feature ветви: `feature/service-name/description`

Для новых функций и улучшений:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/booking-service/add-cancellation-endpoint
```

**Примеры:**
- `feature/notification-service/add-email-support`
- `feature/auth-service/jwt-refresh-token`
- `feature/api-gateway/rate-limiting`
- `feature/room-service/bulk-import`

#### Bugfix ветви: `bugfix/service-name/description`

Для исправления ошибок в develop:

```bash
git checkout develop
git checkout -b bugfix/booking-service/fix-double-booking
```

#### Hotfix ветви: `hotfix/description`

Для критичных исправлений на production:

```bash
git checkout main
git pull origin main
git checkout -b hotfix/database-connection-timeout
```

**⚠️ Важно:** После merging hotfix'а в main, необходимо также mergeить в develop:

```bash
git checkout develop
git merge hotfix/database-connection-timeout
```

#### Release ветви: `release/v*.*.* `

Подготовка к релизу:

```bash
git checkout develop
git checkout -b release/v1.2.0
# Обновить версии
# Тестирование
# Merge в main
```

---

## Соглашения о коммитах

Используем **Conventional Commits** для структурированных сообщений коммитов.

### Формат

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Типы коммитов

| Тип | Описание | Пример |
|-----|---------|--------|
| `feat` | ✨ Новая функция | `feat(auth): add JWT refresh token` |
| `fix` | 🐛 Исправление ошибки | `fix(booking): prevent double booking` |
| `docs` | 📚 Изменения документации | `docs: update API documentation` |
| `style` | 💅 Форматирование кода (не логика) | `style(notification): add linting config` |
| `refactor` | ♻️ Рефакторинг без изменения функции | `refactor(api-gateway): simplify middleware` |
| `perf` | ⚡ Оптимизация производительности | `perf(db): add indexing for queries` |
| `test` | ✅ Добавление/обновление тестов | `test(auth): add JWT validation tests` |
| `chore` | 🔧 Изменения зависимостей, конфига | `chore: update docker-compose versions` |
| `ci` | 🔄 Изменения CI/CD конфига | `ci: add GitHub Actions workflow` |

### Scope (область)

Scope указывает, какой компонент/сервис затронут:

- `auth` - auth-service
- `booking` - booking-service
- `notification` - notification-service
- `room` - room-service
- `schedule` - schedule-service
- `api-gateway` - api-gateway
- `db` - database
- `docker` - Docker-related
- `config` - конфигурация

### Примеры правильных коммитов

```bash
# ✅ Хорошо
git commit -m "feat(notification): add Telegram support"
git commit -m "fix(booking): handle concurrent requests"
git commit -m "docs: add deployment guide"
git commit -m "test(auth): add JWT validation tests"
git commit -m "chore: upgrade Kafka to 7.5.1"

# ❌ Плохо
git commit -m "fix bugs"
git commit -m "updated stuff"
git commit -m "WIP"
```

### Структура подробного коммита

```bash
git commit -m "feat(booking): add cancellation with refund

- Implement refund logic based on cancellation time
- Add cancellation reason tracking
- Update notification service to handle refunds
- Closes #42"
```

---

## Процесс разработки

### 1️⃣ Начало работы над функцией

```bash
# Получить актуальный код
git checkout develop
git pull origin develop

# Создать feature ветвь
git checkout -b feature/booking-service/add-refunds

# Регулярно коммитьте
git add .
git commit -m "feat(booking): add refund entity to database"
```

### 2️⃣ Во время разработки

**Каждый коммит должен быть:**
- ✅ Логически завершённым
- ✅ Проходить локальное тестирование
- ✅ Иметь описательное сообщение

**Плохая практика:**
```bash
git commit -m "WIP"
git commit -m "fix"
git commit -m "another fix"
```

**Хорошая практика:**
```bash
git commit -m "feat(booking): add refund entity"
git commit -m "test(booking): add refund calculation tests"
git commit -m "feat(notification): send refund confirmation"
```

### 3️⃣ Перед push'ем

```bash
# Проверить статус
git status

# Просмотреть изменения
git diff

# Убедиться, что всё скомплировалось/прошло тесты
./run_tests.sh  # если существует

# Push ветвь
git push -u origin feature/booking-service/add-refunds
```

---

## Pull Request процесс

### Создание PR

1. **Push вашу ветвь на GitHub/GitLab**

```bash
git push origin feature/booking-service/add-refunds
```

2. **Создать Pull Request** с title в формате:

```
feat(booking): add refund functionality

Description:
- Adds refund entity to database
- Implements refund calculation logic
- Updates notification service
- Closes #42

Type of change:
- [ ] Bug fix
- [x] New feature
- [ ] Breaking change
- [ ] Documentation update

Testing:
- [ ] Added unit tests
- [ ] Added integration tests
- [ ] Manually tested
```

### Требования к PR

- ✅ PR должен иметь **описание** изменений
- ✅ Все коммиты должны следовать Conventional Commits
- ✅ Локально прошли все тесты
- ✅ Нет конфликтов с `develop`
- ✅ Минимум **1 review** от другого разработчика
- ✅ CI/CD пайплайн успешно прошёл

### Code Review

**Рецензент должен:**
- ✅ Проверить логику кода
- ✅ Проверить соответствие стилю проекта
- ✅ Убедиться в наличии тестов
- ✅ Проверить на проблемы безопасности

**Комментарии:**
```
- Запрашиваете изменения: "Request changes"
- Одобряете: "Approve"
- Комментируете без блокирования: "Comment"
```

### Merge PR

```bash
# После approval все коммиты будут merged в develop
git checkout develop
git pull origin develop
git merge --no-ff feature/booking-service/add-refunds
git push origin develop
```

---

## Релизы

### Подготовка релиза

```bash
# Создать release ветвь из develop
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0

# Обновить версии в коде (если есть)
# - package.json, go.mod версии
# - CHANGELOG.md

# Коммитим изменения версии
git commit -m "chore: bump version to 1.2.0"

# Создаём PR из release/* в main
```

### Завершение релиза

```bash
# Merge в main
git checkout main
git pull origin main
git merge --no-ff release/v1.2.0

# Создаём тег
git tag -a v1.2.0 -m "Release version 1.2.0"

# Merge обратно в develop
git checkout develop
git pull origin develop
git merge --no-ff release/v1.2.0

# Push всё
git push origin main
git push origin develop
git push origin v1.2.0
```

### Обновление CHANGELOG

Файл `CHANGELOG.md` должен содержать историю:

```markdown
# Changelog

## [1.2.0] - 2024-01-15

### Added
- Refund functionality for bookings
- Email support in notification service

### Fixed
- Double booking race condition
- JWT token validation timeout

### Changed
- Updated Kafka to 7.5.1
- Improved error handling in API Gateway

## [1.1.0] - 2023-12-01
...
```

---

## 📌 Правила ветвления

| Ветвь | Создана из | Merge в | Защита |
|------|----------|---------|--------|
| `main` | - | - | ✅ Да |
| `develop` | `main` | - | ✅ Да |
| `feature/*` | `develop` | `develop` | ❌ Нет |
| `bugfix/*` | `develop` | `develop` | ❌ Нет |
| `hotfix/*` | `main` | `main` + `develop` | ❌ Нет |
| `release/*` | `develop` | `main` + `develop` | ❌ Нет |

---

## 🚀 Быстрые команды

```bash
# Создать новую feature ветвь
git checkout -b feature/service-name/description

# Обновить из upstream
git fetch origin
git rebase origin/develop

# Просмотреть историю ветвей
git log --graph --oneline --all --decorate

# Удалить локальную ветвь
git branch -d feature/old-feature

# Удалить удалённую ветвь
git push origin --delete feature/old-feature

# Squash коммитов перед PR (если нужно)
git rebase -i develop

# Cherry-pick коммита (только когда необходимо!)
git cherry-pick <commit-hash>
```

---

## ⚠️ Анти-паттерны (Чего избегать)

❌ **Пушить прямо в main**
❌ **Использовать force push** в shared ветвях
❌ **Коммитить без сообщения** (`git commit -m ""`)
❌ **Оставлять незаконченные ветви** (удалять после merge)
❌ **Мерджить свою же ветвь** (просить review)
❌ **Коммитить зависимости** (package-lock.json, vendor/)
❌ **Коммитить .env файлы** (использовать .env.example)

---

## 📚 Полезные ссылки

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Flow Cheatsheet](https://danielkummer.github.io/git-flow-cheatsheet/)
- [GitHub - Collaborating with Pull Requests](https://docs.github.com/en/pull-requests)

---

**Последнее обновление:** 2024
