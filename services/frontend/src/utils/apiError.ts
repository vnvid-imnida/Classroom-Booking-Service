import axios from 'axios';

/** Extract FastAPI ``detail`` from an axios or unknown error. */
export function getErrorDetail(err: unknown): string | undefined {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    return typeof detail === 'string' ? detail : undefined;
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return undefined;
}

/** HTTP status from an axios error, if present. */
export function getErrorStatus(err: unknown): number | undefined {
  if (axios.isAxiosError(err)) {
    return err.response?.status;
  }
  return undefined;
}
