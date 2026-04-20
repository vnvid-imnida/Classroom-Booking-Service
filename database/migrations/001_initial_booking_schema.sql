BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TYPE request_status AS ENUM ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED');
CREATE TYPE request_action AS ENUM ('CREATE', 'RESCHEDULE');
CREATE TYPE booking_status AS ENUM ('ACTIVE', 'CANCELLED', 'RESCHEDULED', 'COMPLETED');
CREATE TYPE booking_source AS ENUM ('MANUAL', 'RUZ');
CREATE TYPE sync_status AS ENUM ('RUNNING', 'SUCCESS', 'FAILED');

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id bigint NOT NULL UNIQUE,
    telegram_username text NOT NULL UNIQUE,
    full_name text NOT NULL,
    role text NOT NULL CHECK (role IN ('TEACHER', 'MODERATOR', 'ADMIN', 'SYSTEM')),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE buildings (
    id bigserial PRIMARY KEY,
    code text NOT NULL UNIQUE,
    name text NOT NULL,
    address text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rooms (
    id bigserial PRIMARY KEY,
    building_id bigint NOT NULL REFERENCES buildings(id),
    room_number text NOT NULL,
    floor smallint NOT NULL,
    capacity integer NOT NULL CHECK (capacity > 0),
    has_projector boolean NOT NULL DEFAULT false,
    has_whiteboard boolean NOT NULL DEFAULT false,
    is_accessible boolean NOT NULL DEFAULT false,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (building_id, room_number)
);

COMMENT ON COLUMN rooms.is_accessible IS 'Room has barrier-free access for low-mobility groups';

CREATE TABLE event_purposes (
    id smallserial PRIMARY KEY,
    code text NOT NULL UNIQUE,
    name text NOT NULL UNIQUE,
    is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE booking_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    requester_id uuid NOT NULL REFERENCES users(id),
    action request_action NOT NULL DEFAULT 'CREATE',
    target_booking_id uuid,
    room_id bigint NOT NULL REFERENCES rooms(id),
    purpose_id smallint NOT NULL REFERENCES event_purposes(id),
    title text NOT NULL,
    description text,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    status request_status NOT NULL DEFAULT 'DRAFT',
    submitted_at timestamptz,
    moderated_by uuid REFERENCES users(id),
    moderated_at timestamptz,
    moderation_comment text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ends_at > starts_at),
    CHECK (
        (action = 'CREATE' AND target_booking_id IS NULL)
        OR (action = 'RESCHEDULE' AND target_booking_id IS NOT NULL)
    ),
    CHECK ((status <> 'PENDING') OR submitted_at IS NOT NULL),
    CHECK (
        (status NOT IN ('APPROVED', 'REJECTED') AND moderated_at IS NULL AND moderated_by IS NULL)
        OR (status IN ('APPROVED', 'REJECTED') AND moderated_at IS NOT NULL AND moderated_by IS NOT NULL)
    )
);

CREATE TABLE ruz_sync_runs (
    id bigserial PRIMARY KEY,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status sync_status NOT NULL DEFAULT 'RUNNING',
    source_url text NOT NULL DEFAULT 'https://ruz.spbstu.ru/',
    imported_slots_count integer NOT NULL DEFAULT 0,
    error_message text,
    CHECK (
        (status = 'RUNNING' AND finished_at IS NULL)
        OR (status IN ('SUCCESS', 'FAILED') AND finished_at IS NOT NULL)
    )
);

CREATE TABLE bookings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id uuid UNIQUE REFERENCES booking_requests(id),
    organizer_id uuid REFERENCES users(id),
    room_id bigint NOT NULL REFERENCES rooms(id),
    purpose_id smallint REFERENCES event_purposes(id),
    title text NOT NULL,
    description text,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    source booking_source NOT NULL,
    status booking_status NOT NULL DEFAULT 'ACTIVE',
    external_event_id text,
    sync_run_id bigint REFERENCES ruz_sync_runs(id),
    cancelled_by uuid REFERENCES users(id),
    cancelled_at timestamptz,
    cancel_reason text,
    rescheduled_to_booking_id uuid REFERENCES bookings(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ends_at > starts_at),
    CHECK (
        (source = 'MANUAL' AND request_id IS NOT NULL AND organizer_id IS NOT NULL AND purpose_id IS NOT NULL AND external_event_id IS NULL)
        OR (source = 'RUZ' AND request_id IS NULL AND external_event_id IS NOT NULL)
    ),
    CHECK ((status <> 'CANCELLED') OR (cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL)),
    CHECK ((status <> 'RESCHEDULED') OR (rescheduled_to_booking_id IS NOT NULL))
);

ALTER TABLE booking_requests
ADD CONSTRAINT booking_requests_target_booking_fk
FOREIGN KEY (target_booking_id) REFERENCES bookings(id);

ALTER TABLE bookings
ADD CONSTRAINT bookings_no_room_time_overlap
EXCLUDE USING gist (
    room_id WITH =,
    tstzrange(starts_at, ends_at, '[)') WITH &&
)
WHERE (status = 'ACTIVE');

CREATE UNIQUE INDEX bookings_ruz_external_event_uidx
    ON bookings (external_event_id)
    WHERE source = 'RUZ';

CREATE INDEX rooms_filter_idx
    ON rooms (building_id, floor, capacity)
    WHERE is_active = true;

CREATE INDEX bookings_room_time_idx
    ON bookings (room_id, starts_at)
    WHERE status = 'ACTIVE';

CREATE INDEX booking_requests_requester_idx
    ON booking_requests (requester_id, starts_at);

CREATE INDEX booking_requests_status_idx
    ON booking_requests (status, created_at DESC);

CREATE INDEX bookings_organizer_idx
    ON bookings (organizer_id, starts_at DESC);

CREATE OR REPLACE VIEW room_occupancy_grid AS
SELECT
    b.id,
    b.room_id,
    b.starts_at,
    b.ends_at,
    b.title,
    b.source,
    b.status
FROM bookings b
WHERE b.status = 'ACTIVE';

COMMIT;

-- Notifications table (from former 003_notifications_table.sql)
CREATE TABLE IF NOT EXISTS notifications (
    id bigserial PRIMARY KEY,
    telegram_id bigint NOT NULL,
    booking_external_id integer,
    message text NOT NULL,
    notification_type text NOT NULL,
    event_id text NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    sent_at timestamptz,
    failed_reason text
);

CREATE INDEX IF NOT EXISTS notifications_user_created_idx
    ON notifications (telegram_id, created_at DESC);

CREATE INDEX IF NOT EXISTS notifications_event_id_idx
    ON notifications (event_id);

COMMIT;
