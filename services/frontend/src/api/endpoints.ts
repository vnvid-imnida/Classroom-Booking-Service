import { apiClient } from './client';
import type {
  Booking,
  BookingRequestCreatePayload,
  EventPurpose,
  LoginPayload,
  RegisterPayload,
  RegisterResult,
  Room,
  RoomCreatePayload,
  RoomSearchFilters,
  User,
  VerifyEmailPayload,
} from '../types';
import { roleForEmail } from '../utils/emailDomains';
import { moscowDateTimeToUtcIso } from '../utils/dateTime';

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
  purpose_name?: string;
};

function mapBookingStatus(status: string): Booking['status'] {
  const s = status.toUpperCase();
  if (s === 'DRAFT') return 'draft';
  if (s === 'ACTIVE' || s === 'APPROVED' || s === 'COMPLETED') return 'approved';
  if (s === 'PENDING') return 'pending';
  if (s === 'REJECTED') return 'rejected';
  if (s === 'CANCELLED' || s === 'CANCELED' || s === 'RESCHEDULED') return 'cancelled';
  return 'pending';
}

function mapBackendBooking(row: BackendBookingRow, kind: Booking['kind']): Booking {
  const roomLabel =
    row.building_code && row.room_number
      ? `${row.building_code}-${row.room_number}`
      : row.room_number;
  return {
    id: row.id,
    roomId: row.room_number ?? '',
    roomNumber: roomLabel,
    userId: '',
    userName: row.requester_name,
    title: row.title,
    start: row.starts_at,
    end: row.ends_at,
    status: mapBookingStatus(row.status),
    kind,
  };
}

function asBookingRows(data: unknown): BackendBookingRow[] {
  return Array.isArray(data) ? data : [];
}

type BackendRoomRow = {
  id: number;
  building_code: string;
  building_name?: string;
  room_number: string;
  capacity: number;
  has_projector: boolean;
  has_whiteboard?: boolean;
  has_computers?: boolean;
};

function mapBackendRoom(row: BackendRoomRow): Room {
  const hasWhiteboard = Boolean(row.has_whiteboard);
  return {
    id: String(row.id),
    number: row.room_number,
    building: row.building_name || row.building_code,
    buildingCode: row.building_code,
    capacity: row.capacity,
    hasProjector: row.has_projector,
    hasWhiteboard,
    hasComputers: hasWhiteboard,
  };
}

type BackendBuildingRow = {
  id: number;
  code: string;
  name: string;
  address?: string | null;
};

export type BuildingOption = {
  code: string;
  name: string;
};

function asRoomRows(data: unknown): BackendRoomRow[] {
  return Array.isArray(data) ? data : [];
}

export const authApi = {
  login: (payload: LoginPayload) =>
    apiClient
      .post<BackendAuthResponse>('/api/v1/auth/login', {
        email: payload.email.trim().toLowerCase(),
        password: payload.password,
        captcha_token: payload.captchaToken,
      })
      .then((r) => mapAuthResponse(r.data)),
  register: (payload: RegisterPayload) =>
    apiClient
      .post<RegisterResult & { verification_required?: boolean }>(
        '/api/v1/auth/register',
        {
          email: payload.email.trim().toLowerCase(),
          password: payload.password,
          full_name: payload.fullName,
          captcha_token: payload.captchaToken,
        },
      )
      .then((r) => ({
        email: r.data.email,
        message: r.data.message,
      })),
  verifyEmail: (payload: VerifyEmailPayload) =>
    apiClient
      .post<BackendAuthResponse>('/api/v1/auth/verify-email', {
        email: payload.email.trim().toLowerCase(),
        code: payload.code,
      })
      .then((r) => mapAuthResponse(r.data)),
  me: () => apiClient.get<BackendUser>('/api/v1/me').then((r) => mapUser(r.data)),
};

export const buildingsApi = {
  list: () =>
    apiClient.get<BackendBuildingRow[]>('/api/v1/buildings').then((r) =>
      (Array.isArray(r.data) ? r.data : []).map(
        (b): BuildingOption => ({
          code: b.code,
          name: b.name || b.code,
        }),
      ),
    ),
};

export const roomsApi = {
  search: (filters: RoomSearchFilters) => {
    const hasSlot = Boolean(filters.date && filters.fromTime && filters.toTime);
    if (hasSlot) {
      return apiClient
        .get<BackendRoomRow[]>('/api/v1/rooms/available', {
          params: {
            starts_at: moscowDateTimeToUtcIso(filters.date!, filters.fromTime!),
            ends_at: moscowDateTimeToUtcIso(filters.date!, filters.toTime!),
            building_code: filters.building,
            min_capacity: filters.minCapacity,
            has_projector: filters.hasProjector,
            has_whiteboard: filters.hasWhiteboard,
          },
        })
        .then((r) => asRoomRows(r.data).map(mapBackendRoom));
    }
    return apiClient
      .get<BackendRoomRow[]>('/api/v1/rooms', {
        params: {
          building_code: filters.building,
          min_capacity: filters.minCapacity,
          has_projector: filters.hasProjector,
          has_whiteboard: filters.hasWhiteboard,
        },
      })
      .then((r) => asRoomRows(r.data).map(mapBackendRoom));
  },
  list: () =>
    apiClient
      .get<BackendRoomRow[]>('/api/v1/rooms')
      .then((r) => asRoomRows(r.data).map(mapBackendRoom)),
  getById: (id: string) =>
    apiClient.get<BackendRoomRow>(`/api/v1/rooms/${id}`).then((r) => mapBackendRoom(r.data)),
  occupancy: (id: string, date: string) =>
    apiClient
      .get<Array<{ starts_at: string; ends_at: string; title?: string; status?: string }>>(
        `/api/v1/rooms/${id}/occupancy`,
        { params: { date } },
      )
      .then((r) => (Array.isArray(r.data) ? r.data : [])),
  /** Create room (moderator/admin). Maps UI fields to backend body. */
  create: (payload: RoomCreatePayload) =>
    apiClient
      .post<BackendRoomRow>('/api/v1/rooms', {
        building_code: payload.buildingCode ?? payload.building,
        room_number: payload.number,
        capacity: payload.capacity,
        has_projector: payload.hasProjector,
        has_whiteboard: payload.hasWhiteboard,
        is_accessible: payload.isAccessible ?? false,
      })
      .then((r) => mapBackendRoom(r.data)),
  /** Soft-delete room (moderator/admin). */
  remove: (id: string) =>
    apiClient.delete<void>(`/api/v1/rooms/${id}`).then(() => undefined),
};

export const bookingsApi = {
  list: async (params?: {
    from?: string;
    to?: string;
    userId?: string;
    roomId?: string;
    admin?: boolean;
    scope?: 'active' | 'archive';
  }) => {
    if (params?.admin) {
      const res = await apiClient.get<BackendBookingRow[]>('/api/v1/moderation/requests', {
        params: { scope: 'all' },
      });
      return asBookingRows(res.data).map((row) => mapBackendBooking(row, 'request'));
    }

    const scope = params?.scope ?? 'active';
    const [bookingsRes, requestsRes] = await Promise.all([
      apiClient.get<BackendBookingRow[]>('/api/v1/bookings/me', {
        params: { scope },
      }),
      apiClient.get<BackendBookingRow[]>('/api/v1/booking-requests/me', {
        params: { scope },
      }),
    ]);

    return [
      ...asBookingRows(bookingsRes.data).map((row) => mapBackendBooking(row, 'booking')),
      ...asBookingRows(requestsRes.data).map((row) => mapBackendBooking(row, 'request')),
    ];
  },
  create: (payload: BookingRequestCreatePayload) =>
    apiClient
      .post<{ id: string; status: string }>('/api/v1/booking-requests', {
        ...payload,
        action: payload.action ?? 'CREATE',
      })
      .then((r) => r.data),
  submit: (id: string) =>
    apiClient
      .post<{ id: string; status: string }>(`/api/v1/booking-requests/${id}/submit`)
      .then((r) => r.data),
  cancel: (item: Pick<Booking, 'id' | 'kind'>) => {
    const path =
      item.kind === 'request'
        ? `/api/v1/booking-requests/${item.id}/cancel`
        : `/api/v1/bookings/${item.id}/cancel`;
    return apiClient.post<void>(path).then(() => undefined);
  },
  approve: (id: string) =>
    apiClient
      .post<void>(`/api/v1/moderation/requests/${id}/approve`)
      .then(() => undefined),
  reject: (id: string) =>
    apiClient
      .post<void>(`/api/v1/moderation/requests/${id}/reject`, {
        comment: 'Отклонено модератором',
      })
      .then(() => undefined),
};

export const purposesApi = {
  list: () =>
    apiClient
      .get<EventPurpose[]>('/api/v1/event-purposes')
      .then((r) => (Array.isArray(r.data) ? r.data : [])),
};
