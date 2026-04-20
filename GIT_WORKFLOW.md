# Git Workflow Guide

Короткий регламент командной работы с Git.

## Ветви

1. `main` - только релизы, прямые коммиты запрещены.
2. `develop` - интеграционная ветка команды.
3. `feature/<service>/<task>` - новая функциональность.
4. `bugfix/<service>/<task>` - исправления в develop.
5. `hotfix/<task>` - критические правки для main.

## Старт задачи

```bash
git fetch origin
git checkout develop
git pull origin develop
git checkout -b feature/<service>/<task>
```

## Коммиты

Формат: Conventional Commits.

```text
feat(scope): ...
fix(scope): ...
docs: ...
test(scope): ...
refactor(scope): ...
chore: ...
```

Примеры scope: `backend`, `notification`, `parser`, `telegram-frontend`, `generator`, `docker`, `db`.

## Pull Request

1. Цель PR: только `develop` (если это не hotfix).
2. В PR обязательно: описание изменений, шаги проверки, риски/ограничения.
3. Нужен минимум 1 approve.
4. Перед merge ветка должна быть актуальна относительно `develop`.

## Hotfix-процесс

```bash
git checkout main
git pull origin main
git checkout -b hotfix/<task>
```

После merge в `main` изменения обязательно переносятся в `develop`.

## Минимальные запреты

1. Нельзя пушить напрямую в `main`/`develop`.
2. Нельзя использовать неинформативные коммиты (`wip`, `fix`, `update`).
3. Нельзя смешивать несвязанные изменения в одном PR.
