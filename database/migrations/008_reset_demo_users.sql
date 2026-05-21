-- Reset users to two demo accounts (web login + moderation).
-- Clears dependent rows: bookings, booking_requests, telegram_link_tokens.
-- Passwords: test123 (test@spbstu.ru), admin123 (admin@spbstu.ru).
-- Hashes generated via: python -c "from auth_utils import hash_password; ..." in services/backend.

BEGIN;

-- Break circular FK booking_requests <-> bookings before delete.
UPDATE booking_requests SET target_booking_id = NULL, moderated_by = NULL;
UPDATE bookings
SET rescheduled_to_booking_id = NULL,
    cancelled_by = NULL,
    organizer_id = NULL;

DELETE FROM telegram_link_tokens;
DELETE FROM bookings;
DELETE FROM booking_requests;
DELETE FROM users;

INSERT INTO users (id, email, password_hash, full_name, role, is_active)
VALUES
    (
        'a0000001-0001-4001-8001-000000000001',
        'test@spbstu.ru',
        '6c01b699004f233f278a2b732c557907$e209b9d471aa18c9bc0350466fd318611b9fbebce1d51bc463ad37f849d5a66e',
        U&'\0418\0432\0430\043D \0418\0432\0430\043D\043E\0432\0438\0447 \0422\0435\0441\0442\043E\0432',
        'TEACHER',
        true
    ),
    (
        'a0000001-0001-4001-8001-000000000002',
        'admin@spbstu.ru',
        '4d8d5736e7904ad362ada92faf1ee55f$6ddddcc0786691c5cd0c2274e56c93c235c6ac217963d72c1dc179f2dea46626',
        U&'\0410\043D\043D\0430 \041F\0435\0442\0440\043E\0432\043D\0430 \0410\0434\043C\0438\043D\043E\0432\0430',
        'ADMIN',
        true
    );

COMMIT;
