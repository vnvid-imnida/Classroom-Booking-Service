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

export const authApi = {
  login: (payload: LoginPayload) => {
    if (isTestCredentials(payload).ok) {
      return mockAuthApi.login(payload);
    }
    return apiClient
      .post<BackendAuthResponse>('/api/v1/auth/login', payload)
      .then((r) => mapAuthResponse(r.data));
  },
  register: (payload: RegisterPayload) =>
    apiClient
      .post<BackendAuthResponse>('/api/v1/auth/register', {
        email: payload.email.trim().toLowerCase(),
        password: payload.password,
        full_name: payload.fullName,
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
    return apiClient.get<Room[]>('/rooms', { params: filters }).then((r) => r.data);
  },
  list: () => {
    if (isMockMode()) return mockRoomsApi.list();
    return apiClient.get<Room[]>('/rooms').then((r) => r.data);
  },
  getById: (id: string) =>
    apiClient.get<Room>(`/rooms/${id}`).then((r) => r.data),
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
  list: (params?: { from?: string; to?: string; userId?: string; roomId?: string }) => {
    if (isMockMode()) return mockBookingsApi.list(params);
    return apiClient.get<Booking[]>('/bookings', { params }).then((r) => r.data);
  },
  create: (payload: Omit<Booking, 'id' | 'status'>) => {
    if (isMockMode()) return mockBookingsApi.create(payload);
    return apiClient.post<Booking>('/bookings', payload).then((r) => r.data);
  },
  cancel: (id: string) => {
    if (isMockMode()) return mockBookingsApi.cancel(id);
    return apiClient.delete<void>(`/bookings/${id}`).then(() => undefined);
  },
  approve: (id: string) => {
    if (isMockMode()) return mockBookingsApi.approve(id);
    return apiClient.post<void>(`/bookings/${id}/approve`).then(() => undefined);
  },
  reject: (id: string) => {
    if (isMockMode()) return mockBookingsApi.reject(id);
    return apiClient.post<void>(`/bookings/${id}/reject`).then(() => undefined);
  },
};
