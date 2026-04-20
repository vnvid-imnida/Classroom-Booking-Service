№	Таблица	Поле	Размер строки, байт	Число строк (год)	Объем, Мб
1	users	id, email, hash, role	500	30000	15
2	rooms	id, name, capacity, features	1024	500	0.5
3	bookings	id, user_id, room_id, time_start, time_end, status	256	100000	25
4	schedule_cache	room_id, date, json_data	4096	500 * 365	700
5	audit_logs	id, action, user_id, timestamp	128	500000	64
6	notifications	id, user_id, message, status	512	200000	100