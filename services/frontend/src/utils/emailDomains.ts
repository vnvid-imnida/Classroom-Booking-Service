/**
 * SPbPU auth rules — UX mirror of services/auth/ (email_domains.py, roles.py, messages.py).
 * Backend is the source of truth; keep DOMAIN_ERROR_RU and role mapping in sync.
 */

import type { UserRole } from '../types';

export const ALLOWED_EMAIL_DOMAINS = ['spbstu.ru', 'edu.spbstu.ru'] as const;

export const DOMAIN_ERROR_RU =
  'Регистрация и вход доступны только для почты @spbstu.ru или @edu.spbstu.ru';

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

export function emailDomain(email: string): string | null {
  const normalized = normalizeEmail(email);
  if (!normalized.includes('@')) return null;
  const [, domain] = normalized.split('@');
  if (!domain || !domain.includes('.')) return null;
  return domain;
}

export function isAllowedSpbstuEmail(email: string): boolean {
  const domain = emailDomain(email);
  return domain !== null && (ALLOWED_EMAIL_DOMAINS as readonly string[]).includes(domain);
}

/** DB/API role implied by email domain (matches backend role_for_email). */
export function roleForEmail(email: string): UserRole | null {
  const domain = emailDomain(email);
  if (domain === 'edu.spbstu.ru') return 'student';
  if (domain === 'spbstu.ru') return 'teacher';
  return null;
}

/** Russian label for register form hint. */
export function roleLabelForEmail(email: string): string | null {
  const role = roleForEmail(email);
  if (role === 'student') return 'Студент';
  if (role === 'teacher') return 'Преподаватель';
  return null;
}

export function validateSpbstuEmail(email: string): { ok: true } | { ok: false; message: string } {
  const normalized = normalizeEmail(email);
  if (!normalized || !normalized.includes('@')) {
    return { ok: false, message: 'Укажите корректный email.' };
  }
  if (!isAllowedSpbstuEmail(normalized)) {
    return { ok: false, message: DOMAIN_ERROR_RU };
  }
  return { ok: true };
}
