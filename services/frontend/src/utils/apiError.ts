/** FastAPI returns `detail` (string or array); some clients use `message`. */
export function getApiErrorMessage(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
  if (!data) {
    return (err as Error)?.message || fallback;
  }
  const detail = data.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    if (typeof first?.msg === 'string') return first.msg;
  }
  if (typeof data.message === 'string') return data.message;
  return fallback;
}
