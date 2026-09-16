"""Parser service configuration from environment."""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load repo/.env when running locally; no-op in Docker (/app has no parents[2])."""
    here = Path(__file__).resolve()
    candidates: list[Path] = []
    # services/parser/config.py → repo root is parents[2]
    if len(here.parents) > 2:
        candidates.append(here.parents[2] / ".env")
    candidates.append(here.parent / ".env")
    for env_file in candidates:
        if not env_file.is_file():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())
        break


_load_dotenv()

SERVICE_NAME = os.getenv("SERVICE_NAME", "parser")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8082"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://notification_user:notification_password@127.0.0.1:5432/booking",
)

RUZ_BASE_URL = os.getenv("RUZ_BASE_URL", "https://ruz.spbstu.ru/api/v1/ruz").rstrip("/")
RUZ_SYNC_WEEKS = int(os.getenv("RUZ_SYNC_WEEKS", "3"))
RUZ_SYNC_INTERVAL_SECONDS = int(os.getenv("RUZ_SYNC_INTERVAL_SECONDS", "3600"))
RUZ_REQUEST_DELAY_SEC = float(os.getenv("RUZ_REQUEST_DELAY_SEC", "0.2"))
RUZ_HTTP_TIMEOUT_SEC = float(os.getenv("RUZ_HTTP_TIMEOUT_SEC", "30"))

# Our buildings.code → RUZ buildings.abbr (exact match on RUZ side).
# "3" in our DB corresponds to RUZ abbr "3 к.".
BUILDING_CODE_TO_RUZ_ABBR: dict[str, str] = {
    "ГЗ": "ГЗ",
    "3": "3 к.",
}
