-- Test data for notification service
-- Inserts sample data for testing purposes

-- Insert test users
INSERT INTO users (email, hash, role, telegram_id) VALUES
    ('user1@example.com', 'hashed_password_1', 'user', '123456789'),
    ('user2@example.com', 'hashed_password_2', 'user', '987654321'),
    ('user3@example.com', 'hashed_password_3', 'user', NULL),
    ('admin@example.com', 'hashed_password_admin', 'admin', '111111111'),
    ('manager@example.com', 'hashed_password_manager', 'manager', '222222222')
ON CONFLICT (email) DO NOTHING;

-- Insert test rooms
INSERT INTO rooms (name, capacity, features, status) VALUES
    ('Конференц-зал А', 50, ARRAY['projector', 'whiteboard', 'air_conditioning', 'video_conference'], 'available'),
    ('Конференц-зал Б', 30, ARRAY['projector', 'whiteboard', 'video_conference'], 'available'),
    ('Переговорная', 10, ARRAY['whiteboard', 'air_conditioning'], 'available'),
    ('Переговорная 2', 8, ARRAY['whiteboard'], 'maintenance'),
    ('Переговорная 3', 6, ARRAY['air_conditioning'], 'available'),
    ('Зал заседаний', 100, ARRAY['projector', 'whiteboard', 'air_conditioning', 'video_conference', 'sound_system'], 'available')
ON CONFLICT DO NOTHING;

-- Insert test bookings
INSERT INTO bookings (user_id, room_id, time_start, time_end, status, description) VALUES
    (1, 1, CURRENT_TIMESTAMP + INTERVAL '1 day', CURRENT_TIMESTAMP + INTERVAL '1 day 2 hours', 'confirmed', 'Team meeting'),
    (1, 2, CURRENT_TIMESTAMP + INTERVAL '2 days', CURRENT_TIMESTAMP + INTERVAL '2 days 1 hour', 'pending', 'Client presentation'),
    (2, 1, CURRENT_TIMESTAMP + INTERVAL '3 days', CURRENT_TIMESTAMP + INTERVAL '3 days 3 hours', 'confirmed', 'Board meeting'),
    (2, 3, CURRENT_TIMESTAMP + INTERVAL '4 days', CURRENT_TIMESTAMP + INTERVAL '4 days 1 hour', 'confirmed', 'One-on-one'),
    (3, 2, CURRENT_TIMESTAMP + INTERVAL '5 days', CURRENT_TIMESTAMP + INTERVAL '5 days 2 hours', 'cancelled', 'Cancelled meeting'),
    (4, 6, CURRENT_TIMESTAMP + INTERVAL '1 day', CURRENT_TIMESTAMP + INTERVAL '1 day 4 hours', 'confirmed', 'All-hands meeting')
ON CONFLICT DO NOTHING;

-- Insert test schedule cache
INSERT INTO schedule_cache (room_id, date, json_data) VALUES
    (1, CURRENT_DATE, '{"bookings": [{"start": "09:00", "end": "10:00", "user": "user1"}, {"start": "14:00", "end": "15:30", "user": "user2"}]}'),
    (1, CURRENT_DATE + INTERVAL '1 day', '{"bookings": [{"start": "10:00", "end": "12:00", "user": "user3"}]}'),
    (2, CURRENT_DATE, '{"bookings": [{"start": "11:00", "end": "12:00", "user": "user1"}]}'),
    (3, CURRENT_DATE, '{"bookings": []}')
ON CONFLICT (room_id, date) DO UPDATE SET json_data = EXCLUDED.json_data;

-- Insert test notifications
INSERT INTO notifications (user_id, booking_id, message, status, notification_type, delivery_channel) VALUES
    (1, 1, 'Ваше бронирование на завтра в конференц-зале А подтверждено', 'sent', 'booking.created', 'telegram'),
    (1, 2, 'Напоминание: у вас есть забронированная комната на завтра', 'sent', 'booking.reminder', 'email'),
    (2, 3, 'Ваше бронирование конференц-зала Б было обновлено', 'sent', 'booking.updated', 'telegram'),
    (3, 5, 'Ваше бронирование было отменено', 'sent', 'booking.cancelled', 'email'),
    (1, NULL, 'Конференц-зал А требует обслуживания', 'sent', 'room.maintenance', 'telegram'),
    (4, 6, 'Расписание было синхронизировано', 'sent', 'schedule.synced', 'email')
ON CONFLICT DO NOTHING;

-- Insert test audit logs
INSERT INTO audit_logs (action, user_id, details) VALUES
    ('booking.created', 1, '{"booking_id": 1, "room_id": 1}'),
    ('booking.updated', 2, '{"booking_id": 3, "status": "confirmed"}'),
    ('booking.cancelled', 3, '{"booking_id": 5, "reason": "User cancelled"}'),
    ('notification.sent', 1, '{"notification_id": 1, "channel": "telegram"}'),
    ('room.maintenance', 4, '{"room_id": 2, "reason": "Equipment maintenance"}'),
    ('schedule.synced', 4, '{"rooms_count": 6, "duration_ms": 1234}')
ON CONFLICT DO NOTHING;
