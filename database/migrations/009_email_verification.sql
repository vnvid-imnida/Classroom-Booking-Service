BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verified boolean NOT NULL DEFAULT false;

-- Existing web accounts are treated as already verified.
UPDATE users
SET email_verified = true
WHERE email IS NOT NULL AND trim(email) <> '';

CREATE TABLE IF NOT EXISTS email_verification_codes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash text NOT NULL,
    expires_at timestamptz NOT NULL,
    attempts int NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS email_verification_codes_user_id_idx
    ON email_verification_codes (user_id);

CREATE INDEX IF NOT EXISTS email_verification_codes_expires_at_idx
    ON email_verification_codes (expires_at);

COMMIT;
