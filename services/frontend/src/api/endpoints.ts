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
import {
  isMockMode,
  isTestCredentials,
  mockAuthApi,
  mockBookingsApi,
  mockRoomsApi,
} from './mock';

function mapAuthUser(raw: Record<string, unknown>): User {
  const roleRaw = String(raw.role ?? 'student').toLowerCase();
  const role = (roleRaw === 'teacher' ? 'teacher' : roleRaw) as User['role'];
  return {
    id: String(raw.id),
    email: String(raw.email ?? ''),
    fullName: String(raw.full_name ?? raw.fullName ?? ''),
    role,
  };
}

export const authApi = {
  login: (payload: LoginPayload) => {
    // Тестовые учётки → mock
    if (isTestCredentials(payload).ok) {
      return mockAuthApi.login(payload);
    }
    return apiClient
      .post<{ access_token: string; user: Record<string, unknown> }>('/auth/login', payload)
      .then((r) => ({
        token: r.data.access_token,
        user: mapAuthUser(r.data.user),
      }));
  },
  register: (payload: RegisterPayload) =>
    apiClient
      .post<{ access_token: string; user: Record<string, unknown> }>('/auth/register', payload)
      .then((r) => ({
        token: r.data.access_token,
        user: mapAuthUser(r.data.user),
      })),
  me: () => {
    if (isMockMode()) return mockAuthApi.me();
    return apiClient.get<Record<string, unknown>>('/me').then((r) => ({
      id: String(r.data.id),
      email: String(r.data.email ?? ''),
      fullName: String(r.data.full_name ?? r.data.fullName ?? ''),
      role: String(r.data.role ?? 'student').toLowerCase() as User['role'],
    }));
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
