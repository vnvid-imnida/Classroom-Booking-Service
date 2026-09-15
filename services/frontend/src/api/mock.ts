import type { LoginPayload, User } from '../types';

/** Quick-fill credentials for local login forms (must exist in Postgres). */
export const TEST_EMAIL = 'test@spbstu.ru';
export const TEST_PASSWORD = 'test123';

export const ADMIN_EMAIL = 'admin@spbstu.ru';
export const ADMIN_PASSWORD = 'admin123';

/** @deprecated Mock API removed — web uses real backend. Kept for reference only. */
export const MOCK_TOKEN_USER = 'mock-token-spbpu-user';
/** @deprecated */
export const MOCK_TOKEN_ADMIN = 'mock-token-spbpu-admin';

/** @deprecated */
export const MOCK_USER: User = {
  id: 'u-demo-1',
  email: TEST_EMAIL,
  fullName: 'Иван Иванович Тестов',
  role: 'teacher',
};

/** @deprecated */
export const MOCK_ADMIN: User = {
  id: 'u-admin-1',
  email: ADMIN_EMAIL,
  fullName: 'Анна Петровна Админова',
  role: 'admin',
};

/** Always false — mock mode is disabled. */
export function isMockMode(): boolean {
  return false;
}

/** @deprecated No longer used by authApi.login. */
export function isTestCredentials(_payload: LoginPayload): { ok: false } {
  return { ok: false };
}
