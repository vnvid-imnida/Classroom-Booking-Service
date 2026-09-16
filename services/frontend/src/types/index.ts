export type UserRole = 'student' | 'teacher' | 'moderator' | 'admin';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
}

export interface Room {
  id: string;
  number: string;
  building: string;
  /** Building code for API filters (e.g. ГЗ, 3). */
  buildingCode?: string;
  capacity: number;
  hasProjector: boolean;
  hasWhiteboard: boolean;
  isAccessible?: boolean;
  /** @deprecated use hasWhiteboard — kept for older UI bits */
  hasComputers?: boolean;
}

export type BookingStatus = 'pending' | 'approved' | 'rejected' | 'cancelled' | 'draft';

export type BookingKind = 'booking' | 'request';

export interface Booking {
  id: string;
  roomId: string;
  roomNumber?: string;
  userId: string;
  userName?: string;
  title: string;
  start: string; // ISO datetime
  end: string;   // ISO datetime
  status: BookingStatus;
  /** Confirmed booking vs booking request (moderation pipeline). */
  kind: BookingKind;
}

export interface LoginPayload {
  email: string;
  password: string;
  captchaToken?: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  fullName: string;
  captchaToken?: string;
}

export interface RegisterResult {
  email: string;
  message: string;
}

export interface VerifyEmailPayload {
  email: string;
  code: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface RoomSearchFilters {
  /** Building code from API (`ГЗ`, `3`), not display name. */
  building?: string;
  minCapacity?: number;
  hasProjector?: boolean;
  hasWhiteboard?: boolean;
  date?: string;
  fromTime?: string;
  toTime?: string;
}

export type RoomCreatePayload = Omit<Room, 'id'>;

// Локализация
export const STATUS_LABELS: Record<BookingStatus, string> = {
  draft: 'Черновик',
  approved: 'Подтверждено',
  pending: 'На модерации',
  rejected: 'Отклонено',
  cancelled: 'Отменено',
};

export const STATUS_COLORS: Record<BookingStatus, string> = {
  draft: '#757575',
  approved: '#2E7D32',
  pending: '#ED6C02',
  rejected: '#C62828',
  cancelled: '#616161',
};

export const ROLE_LABELS: Record<UserRole, string> = {
  student: 'Студент',
  teacher: 'Преподаватель',
  moderator: 'Модератор',
  admin: 'Администратор',
};

// Роли, которым доступен админ-кабинет
export const ADMIN_ROLES: UserRole[] = ['moderator', 'admin'];

export function isAdminRole(role: UserRole | undefined): boolean {
  return !!role && ADMIN_ROLES.includes(role);
}
