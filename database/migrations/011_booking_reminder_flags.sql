BEGIN;

-- Track 24h / 1h reminder emails for confirmed bookings.
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS reminder_24h_sent_at timestamptz,
    ADD COLUMN IF NOT EXISTS reminder_1h_sent_at timestamptz;

-- Rename if an earlier draft of this migration added reminder_2h_sent_at.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bookings' AND column_name = 'reminder_2h_sent_at'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bookings' AND column_name = 'reminder_24h_sent_at'
    ) THEN
        ALTER TABLE bookings RENAME COLUMN reminder_2h_sent_at TO reminder_24h_sent_at;
    ELSIF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bookings' AND column_name = 'reminder_2h_sent_at'
    ) THEN
        ALTER TABLE bookings DROP COLUMN reminder_2h_sent_at;
    END IF;
END $$;

COMMENT ON COLUMN bookings.reminder_24h_sent_at IS 'When the 24-hour-before email reminder was sent';
COMMENT ON COLUMN bookings.reminder_1h_sent_at IS 'When the 1-hour-before email reminder was sent';

COMMIT;
