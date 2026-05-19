# Frontend — Система бронирования аудиторий СПбПУ

React + TypeScript SPA на Vite.

## Стек

- React 19 + TypeScript + Vite
- React Router 6
- MUI (Material-UI) v5
- TanStack Query (React Query) v5 + axios
- FullCalendar v6 (плагины: dayGrid, timeGrid, interaction)

## Структура

```
src/
  api/            # axios клиент и эндпоинты
  auth/           # AuthContext, провайдер авторизации
  components/     # Layout, ProtectedRoute
  pages/          # LoginPage, SchedulePage, SearchPage, AccountPage
  theme/          # MUI тема (русская локаль)
  types/          # TS-типы модели
  App.tsx         # роутер
  main.tsx        # точка входа: провайдеры (Query, MUI, Auth)
```

## Запуск локально

```bash
cd services/frontend
cp .env.example .env   # при необходимости поправьте VITE_API_BASE_URL
npm install
npm run dev            # http://localhost:5173
```

Прокси на api-gateway настроен в `vite.config.ts` (через `/api/*`).

## Сборка

```bash
npm run build
npm run preview        # локальный просмотр прод-билда
```

## Docker

```bash
docker build -t spbpu-frontend .
docker run --rm -p 8080:80 spbpu-frontend
```

## Демо-режим (без backend)

Для локального просмотра без реального API можно войти с тестовыми данными:

- **Email:** `test@spbstu.ru`
- **Пароль:** `test123`

В этом режиме все API-вызовы перенаправляются на встроенные мок-данные
(см. `src/api/mock.ts`): несколько аудиторий, несколько бронирований на
текущую неделю, тестовый пользователь со статусом "Студент".

На странице входа есть кнопка **"Подставить"**, которая автоматически
заполнит форму тестовыми данными.
