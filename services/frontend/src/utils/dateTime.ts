/** Display booking timestamps in Europe/Moscow (SPbPU / RUZ wall clock). */
const MOSCOW_TZ = 'Europe/Moscow';

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
