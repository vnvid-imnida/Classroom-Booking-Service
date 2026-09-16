"""HTTP client for https://ruz.spbstu.ru JSON API."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from config import RUZ_BASE_URL, RUZ_HTTP_TIMEOUT_SEC, RUZ_REQUEST_DELAY_SEC

logger = logging.getLogger(__name__)


class RuzClient:
    """Thin wrapper around RUZ REST endpoints used for room schedules."""

    def __init__(
        self,
        base_url: str = RUZ_BASE_URL,
        timeout: float = RUZ_HTTP_TIMEOUT_SEC,
        delay_sec: float = RUZ_REQUEST_DELAY_SEC,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.delay_sec = delay_sec
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json", "User-Agent": "spbpu-booking-parser/1.0"})

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if self.delay_sec > 0:
            time.sleep(self.delay_sec)
        url = f"{self.base_url}{path}"
        resp = self._session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def buildings(self) -> list[dict]:
        data = self._get("/buildings")
        return list(data.get("buildings") or [])

    def rooms(self, building_id: int) -> list[dict]:
        data = self._get(f"/buildings/{building_id}/rooms")
        return list(data.get("rooms") or [])

    def room_scheduler(self, building_id: int, room_id: int, date: str) -> dict:
        """Return week schedule for a room; ``date`` is any day in that week (YYYY-MM-DD)."""
        data = self._get(
            f"/buildings/{building_id}/rooms/{room_id}/scheduler",
            params={"date": date},
        )
        return data if isinstance(data, dict) else {}
