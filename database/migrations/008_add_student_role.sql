-- Allow STUDENT role for @edu.spbstu.ru registrations
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check
    CHECK (role IN ('TEACHER', 'STUDENT', 'MODERATOR', 'ADMIN', 'SYSTEM'));
