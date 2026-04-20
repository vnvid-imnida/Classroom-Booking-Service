# spbpu-booking

Минимальная документация проекта для командной разработки.

## Обязательные документы

1. [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - правила ветвления, коммитов и Pull Request.
2. [CONTRIBUTING.md](CONTRIBUTING.md) - ежедневный процесс работы разработчика.
3. [CHANGELOG.md](CHANGELOG.md) - история изменений по релизам.

## Быстрый старт для разработчика

```bash
git clone <repo-url>
cd spbpu-booking

git checkout develop
git pull origin develop
git checkout -b feature/<service>/<task>
```

## Базовые команды

```bash
# запустить общий стек
docker compose up -d

# показать состояние
docker compose ps

# посмотреть логи конкретного сервиса
docker compose logs -f notification-service
```

## Структура для командной работы

```text
services/    # сервисы проекта
.github/     # шаблоны issue/PR
```

Все организационные правила поддерживаются в трех документах выше. Если процесс поменялся, сначала обновляется документация, потом код.
