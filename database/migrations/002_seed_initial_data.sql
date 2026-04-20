BEGIN;

INSERT INTO event_purposes (code, name)
VALUES
    ('LECTURE', 'Лекция'),
    ('EXAM', 'Экзамен'),
    ('MEETING', 'Собрание')
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    is_active = true;

INSERT INTO users (telegram_id, telegram_username, full_name, role)
VALUES
    (1333800382, '@Koshsky', '@Koshsky', 'TEACHER')
ON CONFLICT (telegram_id) DO UPDATE
SET telegram_username = EXCLUDED.telegram_username,
    full_name = EXCLUDED.full_name,
    role = EXCLUDED.role,
    is_active = true;

COMMIT;
