BEGIN;

-- Unicode-escapes: безопасны при накатывании с Windows (PowerShell не ломает кириллицу)
INSERT INTO buildings (code, name, address)
VALUES
        (
            U&'\0413\0417',
            U&'\0413\043B\0430\0432\043D\043E\0435 \0417\0434\0430\043D\0438\0435',
            U&'\0443\043B. \041F\043E\043B\0438\0442\0435\0445\043D\0438\0447\0435\0441\043A\0430\044F, 29'
        ),
    (
        '3',
        U&'3-\0439 \043A\043E\0440\043F\0443\0441',
        U&'\0443\043B. \041F\043E\043B\0438\0442\0435\0445\043D\0438\0447\0435\0441\043A\0430\044F, 29, \043A\043E\0440\043F. 3'
    )
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    address = EXCLUDED.address;

-- Убрать корпуса с битой кодировкой (code = '????'), если такие остались
DELETE FROM rooms
WHERE building_id IN (SELECT id FROM buildings WHERE code = '????');
DELETE FROM buildings WHERE code = '????';

DELETE FROM rooms r
USING buildings b
WHERE r.building_id = b.id
  AND b.code = U&'\0413\0417'
  AND r.room_number IN ('100', '200', '305');

INSERT INTO rooms (building_id, room_number, floor, capacity, has_projector, has_whiteboard, is_accessible)
SELECT b.id, v.room_number, v.floor, v.capacity, v.has_projector, v.has_whiteboard, v.is_accessible
FROM buildings b
JOIN (
    VALUES
        -- Главное здание: лекторий 101, кабинеты 105 / 226 / 302
        (U&'\0413\0417', '101', 1::smallint, 120, true, true, true),
        (U&'\0413\0417', '105', 1::smallint, 20, false, true, false),
        (U&'\0413\0417', '226', 2::smallint, 25, true, true, false),
        (U&'\0413\0417', '302', 3::smallint, 18, false, true, false),
        -- 3-й корпус: кабинеты 109, 110, 209, 216 (этаж = первая цифра)
        ('3', '109', 1::smallint, 20, false, true, false),
        ('3', '110', 1::smallint, 20, false, true, false),
        ('3', '209', 2::smallint, 25, true, true, false),
        ('3', '216', 2::smallint, 25, true, false, false)
) AS v(building_code, room_number, floor, capacity, has_projector, has_whiteboard, is_accessible)
  ON v.building_code = b.code
ON CONFLICT (building_id, room_number) DO UPDATE
SET floor = EXCLUDED.floor,
    capacity = EXCLUDED.capacity,
    has_projector = EXCLUDED.has_projector,
    has_whiteboard = EXCLUDED.has_whiteboard,
    is_accessible = EXCLUDED.is_accessible,
    is_active = true;

DELETE FROM rooms r
USING buildings b
WHERE r.building_id = b.id
  AND b.code = '3'
  AND r.room_number IN ('101', '215', '308');

COMMIT;
