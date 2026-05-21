-- Fix demo user full_name encoding (008 may have been applied with wrong client encoding).
BEGIN;

UPDATE users
SET full_name = U&'\0418\0432\0430\043D \0418\0432\0430\043D\043E\0432\0438\0447 \0422\0435\0441\0442\043E\0432'
WHERE lower(email) = 'test@spbstu.ru';

UPDATE users
SET full_name = U&'\0410\043D\043D\0430 \041F\0435\0442\0440\043E\0432\043D\0430 \0410\0434\043C\0438\043D\043E\0432\0430'
WHERE lower(email) = 'admin@spbstu.ru';

COMMIT;
