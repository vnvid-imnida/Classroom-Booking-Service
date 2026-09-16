BEGIN;

-- System actor for automatic cancellations (e.g. RUZ schedule overrides MANUAL bookings).
INSERT INTO users (id, email, full_name, role, is_active, email_verified)
VALUES (
    '00000000-0000-4000-8000-000000000001',
    'system@spbpu-booking.local',
    'SPbPU Booking System',
    'SYSTEM',
    true,
    true
)
ON CONFLICT (id) DO UPDATE
SET full_name = EXCLUDED.full_name,
    role = 'SYSTEM',
    is_active = true,
    email_verified = true;

COMMIT;
