# Contributing to spbpu-booking

Этот документ содержит только обязательные правила для командной разработки.

## Перед началом работы

1. Прочитайте [GIT_WORKFLOW.md](GIT_WORKFLOW.md).
2. Работайте только через feature/bugfix ветки.
3. Не коммитьте напрямую в `main` и `develop`.

## Ежедневный цикл разработчика

```bash
git fetch origin
git checkout develop
git pull origin develop
git checkout -b feature/<service>/<task>
```

После изменений:

```bash
git add <files>
git commit -m "feat(scope): short description"
git push -u origin feature/<service>/<task>
```

## Обязательные требования к PR

1. PR создается только в `develop`.
2. Минимум 1 review от другого разработчика.
3. Все локальные проверки и тесты проходят.
4. В описании PR есть: что изменено, как проверено, риски.

Шаблон PR находится в [.github/pull_request_template.md](.github/pull_request_template.md).

## Коммиты

Используем Conventional Commits:

```text
feat(scope): ...
fix(scope): ...
docs: ...
refactor(scope): ...
test(scope): ...
chore: ...
```

Плохие сообщения (`fix`, `wip`, `updated`) не допускаются.

## Минимальный чек-лист перед push

1. `git diff --staged` проверен.
2. Нет случайных файлов в коммите.
3. Обновлена документация, если поменялся процесс.
