-- Initialize database schema for notification service
-- This file runs all migrations in order

\echo 'Creating notification service database schema...'

-- Migration 0001: Create users table
\echo 'Running migration 0001: Create users table'
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    telegram_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- Migration 0002: Create rooms table
\echo 'Running migration 0002: Create rooms table'
CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    capacity INTEGER NOT NULL,
    features TEXT[] DEFAULT ARRAY[]::TEXT[],
    status VARCHAR(50) DEFAULT 'available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rooms_name ON rooms(name);
CREATE INDEX IF NOT EXISTS idx_rooms_status ON rooms(status);

-- Migration 0003: Create bookings table
\echo 'Running migration 0003: Create bookings table'
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    time_start TIMESTAMP NOT NULL,
    time_end TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_room_id ON bookings(room_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_time_start ON bookings(time_start);
CREATE INDEX IF NOT EXISTS idx_bookings_time_end ON bookings(time_end);

-- Migration 0004: Create schedule_cache table
\echo 'Running migration 0004: Create schedule_cache table'
CREATE TABLE IF NOT EXISTS schedule_cache (
    id SERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    json_data JSONB NOT NULL,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(room_id, date)
);

CREATE INDEX IF NOT EXISTS idx_schedule_cache_room_date ON schedule_cache(room_id, date);
CREATE INDEX IF NOT EXISTS idx_schedule_cache_synced_at ON schedule_cache(synced_at);

-- Migration 0005: Create notifications table
\echo 'Running migration 0005: Create notifications table'
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    booking_id INTEGER REFERENCES bookings(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    notification_type VARCHAR(50) NOT NULL DEFAULT 'booking',
    event_id UUID,
    delivery_channel VARCHAR(50),
    sent_at TIMESTAMP,
    failed_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_event_id ON notifications(event_id);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_booking_id ON notifications(booking_id);

-- Migration 0006: Create audit_logs table
\echo 'Running migration 0006: Create audit_logs table'
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(255) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);

-- Migration 0001: Insert test data
\echo 'Running migration 0001: Insert test data'
INSERT INTO users (email, hash, role, telegram_id) VALUES
    ('user1@example.com', 'hashed_password_1', 'user', '123456789'),
    ('user2@example.com', 'hashed_password_2', 'user', '987654321'),
    ('user3@example.com', 'hashed_password_3', 'user', NULL),
    ('admin@example.com', 'hashed_password_admin', 'admin', '111111111'),
    ('manager@example.com', 'hashed_password_manager', 'manager', '222222222')
ON CONFLICT (email) DO NOTHING;

INSERT INTO rooms (name, capacity, features, status) VALUES
    ('Конференц-зал А', 50, ARRAY['projector', 'whiteboard', 'air_conditioning', 'video_conference'], 'available'),
    ('Конференц-зал Б', 30, ARRAY['projector', 'whiteboard', 'video_conference'], 'available'),
    ('Переговорная', 10, ARRAY['whiteboard', 'air_conditioning'], 'available'),
    ('Переговорная 2', 8, ARRAY['whiteboard'], 'maintenance'),
    ('Переговорная 3', 6, ARRAY['air_conditioning'], 'available'),
    ('Зал заседаний', 100, ARRAY['projector', 'whiteboard', 'air_conditioning', 'video_conference', 'sound_system'], 'available')
ON CONFLICT DO NOTHING;

INSERT INTO bookings (user_id, room_id, time_start, time_end, status, description) VALUES
    (1, 1, CURRENT_TIMESTAMP + INTERVAL '1 day', CURRENT_TIMESTAMP + INTERVAL '1 day 2 hours', 'confirmed', 'Team meeting'),
    (1, 2, CURRENT_TIMESTAMP + INTERVAL '2 days', CURRENT_TIMESTAMP + INTERVAL '2 days 1 hour', 'pending', 'Client presentation'),
    (2, 1, CURRENT_TIMESTAMP + INTERVAL '3 days', CURRENT_TIMESTAMP + INTERVAL '3 days 3 hours', 'confirmed', 'Board meeting'),
    (2, 3, CURRENT_TIMESTAMP + INTERVAL '4 days', CURRENT_TIMESTAMP + INTERVAL '4 days 1 hour', 'confirmed', 'One-on-one'),
    (3, 2, CURRENT_TIMESTAMP + INTERVAL '5 days', CURRENT_TIMESTAMP + INTERVAL '5 days 2 hours', 'cancelled', 'Cancelled meeting'),
    (4, 6, CURRENT_TIMESTAMP + INTERVAL '1 day', CURRENT_TIMESTAMP + INTERVAL '1 day 4 hours', 'confirmed', 'All-hands meeting')
ON CONFLICT DO NOTHING;

INSERT INTO schedule_cache (room_id, date, json_data) VALUES
    (1, CURRENT_DATE, '{"bookings": [{"start": "09:00", "end": "10:00", "user": "user1"}, {"start": "14:00", "end": "15:30", "user": "user2"}]}'),
    (1, CURRENT_DATE + INTERVAL '1 day', '{"bookings": [{"start": "10:00", "end": "12:00", "user": "user3"}]}'),
    (2, CURRENT_DATE, '{"bookings": [{"start": "11:00", "end": "12:00", "user": "user1"}]}'),
    (3, CURRENT_DATE, '{"bookings": []}')
ON CONFLICT (room_id, date) DO UPDATE SET json_data = EXCLUDED.json_data;

INSERT INTO notifications (user_id, booking_id, message, status, notification_type, delivery_channel) VALUES
    (1, 1, 'Ваше бронирование на завтра в конференц-зале А подтверждено', 'sent', 'booking.created', 'telegram'),
    (1, 2, 'Напоминание: у вас есть забронированная комната на завтра', 'sent', 'booking.reminder', 'email'),
    (2, 3, 'Ваше бронирование конференц-зала Б было обновлено', 'sent', 'booking.updated', 'telegram'),
    (3, 5, 'Ваше бронирование было отменено', 'sent', 'booking.cancelled', 'email'),
    (1, NULL, 'Конференц-зал А требует обслуживания', 'sent', 'room.maintenance', 'telegram'),
    (4, 6, 'Расписание было синхронизировано', 'sent', 'schedule.synced', 'email')
ON CONFLICT DO NOTHING;

INSERT INTO audit_logs (action, user_id, details) VALUES
    ('booking.created', 1, '{"booking_id": 1, "room_id": 1}'),
    ('booking.updated', 2, '{"booking_id": 3, "status": "confirmed"}'),
    ('booking.cancelled', 3, '{"booking_id": 5, "reason": "User cancelled"}'),
    ('notification.sent', 1, '{"notification_id": 1, "channel": "telegram"}'),
    ('room.maintenance', 4, '{"room_id": 2, "reason": "Equipment maintenance"}'),
    ('schedule.synced', 4, '{"rooms_count": 6, "duration_ms": 1234}')
ON CONFLICT DO NOTHING;

\echo 'Database initialization completed successfully!'
