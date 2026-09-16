/** Display booking timestamps in Europe/Moscow (SPbPU / RUZ wall clock). */
const MOSCOW_TZ = 'Europe/Moscow';

/** RUZ / SPbPU full-time pair slots (Moscow wall clock). */
export const RUZ_TIME_SLOTS: ReadonlyArray<{ start: string; end: string; label: string }> = [
  { start: '08:00', end: '09:40', label: '08:00 — 09:40' },
  { start: '10:00', end: '11:40', label: '10:00 — 11:40' },
  { start: '12:00', end: '13:40', label: '12:00 — 13:40' },
  { start: '14:00', end: '15:40', label: '14:00 — 15:40' },
  { start: '16:00', end: '17:40', label: '16:00 — 17:40' },
  { start: '18:00', end: '19:40', label: '18:00 — 19:40' },
];

export function formatMoscowDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString('ru-RU', { timeZone: MOSCOW_TZ });
  } catch {
    return iso;
  }
}

export function formatMoscowRange(start: string, end: string): string {
  return `${formatMoscowDateTime(start)} — ${formatMoscowDateTime(end)}`;
}

/**
 * Build a UTC ISO string for a Moscow calendar date + ``HH:mm`` wall time.
 * Example: ``moscowDateTimeToUtcIso('2026-09-17', '08:00')`` → ``2026-09-17T05:00:00.000Z``
 */
export function moscowDateTimeToUtcIso(date: string, hm: string): string {
  const [y, m, d] = date.split('-').map(Number);
  const [hh, mm] = hm.split(':').map(Number);
  // Moscow has been permanently UTC+3 since 2014 (no DST).
  const asUtcMs = Date.UTC(y, m - 1, d, hh, mm, 0) - 3 * 60 * 60 * 1000;
  return new Date(asUtcMs).toISOString();
}

function rangesOverlap(start1: number, end1: number, start2: number, end2: number): boolean {
  return start1 < end2 && end1 > start2;
}

/** Free RUZ pair slots for a Moscow calendar day given occupancy intervals. */
export function freeRuzSlots(
  date: string,
  occupancy: Array<{ starts_at: string; ends_at: string }>,
): typeof RUZ_TIME_SLOTS[number][] {
  return RUZ_TIME_SLOTS.filter((slot) => {
    const start = new Date(moscowDateTimeToUtcIso(date, slot.start)).getTime();
    const end = new Date(moscowDateTimeToUtcIso(date, slot.end)).getTime();
    return !occupancy.some((occ) => {
      const os = new Date(occ.starts_at).getTime();
      const oe = new Date(occ.ends_at).getTime();
      return rangesOverlap(start, end, os, oe);
    });
  });
}

/** Free RUZ pair labels for a Moscow calendar day given occupancy intervals. */
export function freeRuzSlotLabels(
  date: string,
  occupancy: Array<{ starts_at: string; ends_at: string }>,
): string[] {
  return freeRuzSlots(date, occupancy).map((s) => s.label);
}
