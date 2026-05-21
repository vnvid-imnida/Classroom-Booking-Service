BEGIN;

ALTER TABLE users
    ALTER COLUMN telegram_id DROP NOT NULL,
    ALTER COLUMN telegram_username DROP NOT NULL;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email text,
    ADD COLUMN IF NOT EXISTS password_hash text;

CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_idx
    ON users (lower(email))
    WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS telegram_link_tokens (
    token text PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS telegram_link_tokens_user_id_idx
    ON telegram_link_tokens (user_id);

COMMIT;
