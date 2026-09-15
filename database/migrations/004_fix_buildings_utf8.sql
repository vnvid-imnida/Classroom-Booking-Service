BEGIN;

UPDATE buildings SET name = 'Корпус 1', address = 'Политехническая, 29' WHERE code = '1';
UPDATE buildings SET name = 'Корпус 2', address = 'Политехническая, 29' WHERE code = '2';

COMMIT;
