import { apiClient } from './client';
import type {
  Booking,
  LoginPayload,
  RegisterPayload,
  Room,
  RoomCreatePayload,
  RoomSearchFilters,
  User,
} from '../types';
import { roleForEmail } from '../utils/emailDomains';
import {
  isMockMode,
  isTestCredentials,
  mockAuthApi,
  mockBookingsApi,
  mockRoomsApi,
} from './mock';

type BackendUser = {
  id: string;
  email?: string;
  full_name?: string;
  fullName?: string;
  role?: string;
};

type BackendAuthResponse = {
  access_token?: string;
  token?: string;
  user: BackendUser;
};

function mapRole(role?: string): User['role'] {
  const r = (role || 'TEACHER').toLowerCase();
  if (r === 'admin') return 'admin';
  if (r === 'moderator') return 'moderator';
  if (r === 'student') return 'student';
  return 'teacher';
}

/** Prefer domain-based student/teacher; keep moderator/admin from API. */
function resolveUserRole(raw: BackendUser): User['role'] {
  const email = raw.email || '';
  const fromApi = mapRole(raw.role);
  const fromDomain = roleForEmail(email);
  if (fromApi === 'admin' || fromApi === 'moderator') return fromApi;
  if (fromDomain) return fromDomain;
  return fromApi;
}

function mapUser(raw: BackendUser): User {
  return {
    id: raw.id,
    email: raw.email || '',
    fullName: raw.full_name || raw.fullName || '',
    role: resolveUserRole(raw),
  };
}

function mapAuthResponse(data: BackendAuthResponse) {
  const token = data.access_token || data.token;
  if (!token) throw new Error('Ответ API без токена');
  return { token, user: mapUser(data.user) };
}

type BackendBookingRow = {
  id: string;
  status: string;
  title: string;
  starts_at: string;
  ends_at: string;
  building_code?: string;
  room_number?: string;
  requester_name?: string;
};

function mapBookingStatus(status: string): Booking['status'] {
  const s = status.toUpperCase();
  if (s === 'ACTIVE' || s === 'APPROVED') return 'approved';
  if (s === 'PENDING' || s === 'DRAFT') return 'pending';
  if (s === 'REJECTED') return 'rejected';
  if (s === 'CANCELLED' || s === 'CANCELED') return 'cancelled';
  return 'pending';
}

function mapBackendBooking(row: BackendBookingRow): Booking {
  return {
    id: row.id,
    roomId: row.room_number ?? '',
    roomNumber: row.room_number,
    userId: '',
    userName: row.requester_name,
    title: row.title,
    start: row.starts_at,
    end: row.ends_at,
    status: mapBookingStatus(row.status),
  };
}

function asBookingRows(data: unknown): BackendBookingRow[] {
  return Array.isArray(data) ? data : [];
}

type BackendRoomRow = {
  id: number;
  building_code: string;
  building_name: string;
  room_number: string;
  capacity: number;
  has_projector: boolean;
  has_whiteboard?: boolean;
  has_computers?: boolean;
};

function mapBackendRoom(row: BackendRoomRow): Room {
  return {
    id: String(row.id),
    number: row.room_number,
    building: row.building_name || row.building_code,
    capacity: row.capacity,
    hasProjector: row.has_projector,
    hasComputers: row.has_computers ?? false,
  };
}

function asRoomRows(data: unknown): BackendRoomRow[] {
  return Array.isArray(data) ? data : [];
}

export const authApi = {
  login: (payload: LoginPayload) => {
    if (isTestCredentials(payload).ok) {
      return mockAuthApi.login(payload);
    }
    return apiClient
      .post<BackendAuthResponse>('/api/v1/auth/login', {
        email: payload.email.trim().toLowerCase(),
        password: payload.password,
        captcha_token: payload.captchaToken,
      })
      .then((r) => mapAuthResponse(r.data));
  },
  register: (payload: RegisterPayload) =>
    apiClient
      .post<BackendAuthResponse>('/api/v1/auth/register', {
        email: payload.email.trim().toLowerCase(),
        password: payload.password,
        full_name: payload.fullName,
        captcha_token: payload.captchaToken,
      })
      .then((r) => mapAuthResponse(r.data)),
  me: () => {
    if (isMockMode()) return mockAuthApi.me();
    return apiClient.get<BackendUser>('/api/v1/me').then((r) => mapUser(r.data));
  },
};

export const roomsApi = {
  search: (filters: RoomSearchFilters) => {
    if (isMockMode()) return mockRoomsApi.search(filters);
    return apiClient
      .get<BackendRoomRow[]>('/api/v1/rooms', {
        params: {
          building_code: filters.building,
          min_capacity: filters.minCapacity,
          has_projector: filters.hasProjector,
        },
      })
      .then((r) => asRoomRows(r.data).map(mapBackendRoom));
  },
  list: () => {
    if (isMockMode()) return mockRoomsApi.list();
    return apiClient
      .get<BackendRoomRow[]>('/api/v1/rooms')
      .then((r) => asRoomRows(r.data).map(mapBackendRoom));
  },
  getById: (id: string) =>
    apiClient.get<BackendRoomRow>(`/api/v1/rooms/${id}`).then((r) => mapBackendRoom(r.data)),
  create: (payload: RoomCreatePayload) => {
    if (isMockMode()) return mockRoomsApi.create(payload);
    return apiClient.post<Room>('/rooms', payload).then((r) => r.data);
  },
  remove: (id: string) => {
    if (isMockMode()) return mockRoomsApi.remove(id);
    return apiClient.delete<void>(`/rooms/${id}`).then(() => undefined);
  },
};

export const bookingsApi = {
  list: async (params?: {
    from?: string;
    to?: string;
    userId?: string;
    roomId?: string;
    admin?: boolean;
  }) => {
    if (isMockMode()) return mockBookingsApi.list(params);

    if (params?.admin) {
      const res = await apiClient.get<BackendBookingRow[]>('/api/v1/moderation/requests');
      return asBookingRows(res.data).map(mapBackendBooking);
    }

    const [bookingsRes, requestsRes] = await Promise.all([
      apiClient.get<BackendBookingRow[]>('/api/v1/bookings/me', {
        params: { scope: 'active' },
      }),
      apiClient.get<BackendBookingRow[]>('/api/v1/booking-requests/me', {
        params: { scope: 'active' },
      }),
    ]);

    return [
      ...asBookingRows(bookingsRes.data).map(mapBackendBooking),
      ...asBookingRows(requestsRes.data).map(mapBackendBooking),
    ];
  },
  create: (payload: Omit<Booking, 'id' | 'status'>) => {
    if (isMockMode()) return mockBookingsApi.create(payload);
    return apiClient.post<Booking>('/bookings', payload).then((r) => r.data);
  },
  cancel: (id: string) => {
    if (isMockMode()) return mockBookingsApi.cancel(id);
    return apiClient
      .post<void>(`/api/v1/bookings/${id}/cancel`)
      .then(() => undefined);
  },
  approve: (id: string) => {
    if (isMockMode()) return mockBookingsApi.approve(id);
    return apiClient
      .post<void>(`/api/v1/moderation/requests/${id}/approve`)
      .then(() => undefined);
  },
  reject: (id: string) => {
    if (isMockMode()) return mockBookingsApi.reject(id);
    return apiClient
      .post<void>(`/api/v1/moderation/requests/${id}/reject`, {
        comment: 'Отклонено модератором',
      })
      .then(() => undefined);
  },
};
