BEGIN;

INSERT INTO buildings (code, name, address)
VALUES
    ('1', 'Корпус 1', 'Политехническая, 29'),
    ('2', 'Корпус 2', 'Политехническая, 29')
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    address = EXCLUDED.address;

INSERT INTO rooms (building_id, room_number, floor, capacity, has_projector, has_whiteboard, is_accessible)
SELECT b.id, v.room_number, v.floor, v.capacity, v.has_projector, v.has_whiteboard, v.is_accessible
FROM buildings b
JOIN (
    VALUES
        ('1', '101', 1, 30, true, true, false),
        ('1', '205', 2, 50, true, true, true),
        ('2', '301', 3, 40, true, false, false),
        ('2', '402', 4, 25, false, true, false)
) AS v(building_code, room_number, floor, capacity, has_projector, has_whiteboard, is_accessible)
    ON b.code = v.building_code
ON CONFLICT (building_id, room_number) DO UPDATE
SET floor = EXCLUDED.floor,
    capacity = EXCLUDED.capacity,
    has_projector = EXCLUDED.has_projector,
    has_whiteboard = EXCLUDED.has_whiteboard,
    is_accessible = EXCLUDED.is_accessible,
    is_active = true;

COMMIT;
