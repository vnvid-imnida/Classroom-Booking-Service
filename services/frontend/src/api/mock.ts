import type {
  Booking, LoginPayload, Room, RoomCreatePayload, RoomSearchFilters, User,
} from '../types';

// Учётные данные тестовых пользователей (только для локальной разработки)
export const TEST_EMAIL = 'test@spbstu.ru';
export const TEST_PASSWORD = 'test123';

export const ADMIN_EMAIL = 'admin@spbstu.ru';
export const ADMIN_PASSWORD = 'admin123';

export const MOCK_TOKEN_USER  = 'mock-token-spbpu-user';
export const MOCK_TOKEN_ADMIN = 'mock-token-spbpu-admin';

export const MOCK_USER: User = {
  id: 'u-demo-1',
  email: TEST_EMAIL,
  fullName: 'Иван Иванович Тестов',
  role: 'teacher',
};

export const MOCK_ADMIN: User = {
  id: 'u-admin-1',
  email: ADMIN_EMAIL,
  fullName: 'Анна Петровна Админова',
  role: 'admin',
};

let MOCK_ROOMS: Room[] = [
  { id: 'r1', number: '101',  building: 'Главный',     capacity: 30,  hasProjector: true,  hasComputers: false },
  { id: 'r2', number: '215',  building: 'Главный',     capacity: 60,  hasProjector: true,  hasComputers: true  },
  { id: 'r3', number: '402',  building: '2-й',         capacity: 20,  hasProjector: false, hasComputers: false },
  { id: 'r4', number: '105',  building: '3-й',         capacity: 100, hasProjector: true,  hasComputers: false },
  { id: 'r5', number: '311',  building: '4-й',         capacity: 25,  hasProjector: false, hasComputers: true  },
  { id: 'r6', number: '201',  building: 'Гидрокорпус', capacity: 40,  hasProjector: true,  hasComputers: false },
  { id: 'r7', number: '317а', building: 'Главный',     capacity: 15,  hasProjector: false, hasComputers: true  },
];

// Генерируем брони на текущую неделю
function generateBookings(): Booking[] {
  const today = new Date();
  const monday = new Date(today);
  const day = today.getDay();
  monday.setDate(today.getDate() - ((day + 6) % 7));
  monday.setHours(0, 0, 0, 0);

  const at = (dayOffset: number, hour: number, minute = 0) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + dayOffset);
    d.setHours(hour, minute, 0, 0);
    return d.toISOString();
  };

  return [
    {
      id: 'b1', roomId: 'r1', roomNumber: '101', userId: MOCK_USER.id, userName: MOCK_USER.fullName,
      title: 'Алгоритмы и структуры данных',
      start: at(0, 10), end: at(0, 11, 30),
      status: 'approved',
    },
    {
      id: 'b2', roomId: 'r2', roomNumber: '215', userId: MOCK_USER.id, userName: MOCK_USER.fullName,
      title: 'Семинар по математическому анализу',
      start: at(1, 14), end: at(1, 15, 30),
      status: 'approved',
    },
    {
      id: 'b3', roomId: 'r4', roomNumber: '105', userId: MOCK_USER.id, userName: MOCK_USER.fullName,
      title: 'Защита курсовой работы',
      start: at(2, 12), end: at(2, 14),
      status: 'pending',
    },
    {
      id: 'b4', roomId: 'r3', roomNumber: '402', userId: MOCK_USER.id, userName: MOCK_USER.fullName,
      title: 'Консультация научного руководителя',
      start: at(3, 16), end: at(3, 17),
      status: 'approved',
    },
    {
      id: 'b5', roomId: 'r5', roomNumber: '311', userId: MOCK_USER.id, userName: MOCK_USER.fullName,
      title: 'Лабораторная по программированию',
      start: at(4, 9),  end: at(4, 12),
      status: 'rejected',
    },
    {
      id: 'b6', roomId: 'r6', roomNumber: '201', userId: 'u-other-1', userName: 'Пётр Сергеев',
      title: 'Встреча студсовета',
      start: at(2, 18), end: at(2, 19, 30),
      status: 'pending',
    },
    {
      id: 'b7', roomId: 'r1', roomNumber: '101', userId: 'u-other-2', userName: 'Мария Кузнецова',
      title: 'Кружок робототехники',
      start: at(3, 18), end: at(3, 20),
      status: 'pending',
    },
  ];
}

let MOCK_BOOKINGS: Booking[] = generateBookings();

// Mock-режим активен, если в localStorage лежит наш токен
export function isMockMode(): boolean {
  if (typeof localStorage === 'undefined') return false;
  const t = localStorage.getItem('auth_token');
  return t === MOCK_TOKEN_USER || t === MOCK_TOKEN_ADMIN;
}

function currentMockUser(): User | null {
  if (typeof localStorage === 'undefined') return null;
  const t = localStorage.getItem('auth_token');
  if (t === MOCK_TOKEN_USER)  return MOCK_USER;
  if (t === MOCK_TOKEN_ADMIN) return MOCK_ADMIN;
  return null;
}

export function isTestCredentials(payload: LoginPayload): {
  ok: true; user: User; token: string;
} | { ok: false } {
  const email = payload.email.trim().toLowerCase();
  if (email === TEST_EMAIL  && payload.password === TEST_PASSWORD)  return { ok: true, user: MOCK_USER,  token: MOCK_TOKEN_USER  };
  if (email === ADMIN_EMAIL && payload.password === ADMIN_PASSWORD) return { ok: true, user: MOCK_ADMIN, token: MOCK_TOKEN_ADMIN };
  return { ok: false };
}

// Небольшая задержка чтобы UI чувствовался "живым"
const delay = (ms = 250) => new Promise<void>((r) => setTimeout(r, ms));

export const mockAuthApi = {
  async login(payload: LoginPayload) {
    await delay();
    const res = isTestCredentials(payload);
    if (!res.ok) throw new Error('Неверные тестовые учётные данные');
    return { token: res.token, user: res.user };
  },
  async me(): Promise<User> {
    await delay(100);
    const u = currentMockUser();
    if (!u) throw new Error('Mock пользователь не найден');
    return u;
  },
};

export const mockRoomsApi = {
  async search(filters: RoomSearchFilters): Promise<Room[]> {
    await delay();
    return MOCK_ROOMS.filter((r) => {
      if (filters.building && r.building !== filters.building) return false;
      if (filters.minCapacity && r.capacity < filters.minCapacity) return false;
      if (filters.hasProjector && !r.hasProjector) return false;
      if (filters.hasComputers && !r.hasComputers) return false;
      return true;
    });
  },
  async list(): Promise<Room[]> {
    await delay();
    return [...MOCK_ROOMS];
  },
  async create(payload: RoomCreatePayload): Promise<Room> {
    await delay();
    const room: Room = { id: `r-new-${Date.now()}`, ...payload };
    MOCK_ROOMS = [...MOCK_ROOMS, room];
    return room;
  },
  async remove(id: string): Promise<void> {
    await delay();
    MOCK_ROOMS = MOCK_ROOMS.filter((r) => r.id !== id);
  },
};

export const mockBookingsApi = {
  async list(params?: { userId?: string; roomId?: string }): Promise<Booking[]> {
    await delay();
    return MOCK_BOOKINGS.filter((b) => {
      if (params?.userId && b.userId !== params.userId) return false;
      if (params?.roomId && b.roomId !== params.roomId) return false;
      return true;
    });
  },
  async cancel(id: string): Promise<void> {
    await delay();
    MOCK_BOOKINGS = MOCK_BOOKINGS.map((b) =>
      b.id === id ? { ...b, status: 'cancelled' as const } : b,
    );
  },
  async create(payload: Omit<Booking, 'id' | 'status'>): Promise<Booking> {
    await delay();
    const b: Booking = { id: `b-new-${Date.now()}`, status: 'pending', ...payload };
    MOCK_BOOKINGS = [...MOCK_BOOKINGS, b];
    return b;
  },
  async approve(id: string): Promise<void> {
    await delay();
    MOCK_BOOKINGS = MOCK_BOOKINGS.map((b) =>
      b.id === id ? { ...b, status: 'approved' as const } : b,
    );
  },
  async reject(id: string): Promise<void> {
    await delay();
    MOCK_BOOKINGS = MOCK_BOOKINGS.map((b) =>
      b.id === id ? { ...b, status: 'rejected' as const } : b,
    );
  },
};
