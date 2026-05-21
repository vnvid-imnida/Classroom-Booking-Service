# Uses PEP 8
# Tools: black, flake8, mypy

from typing import Any

import httpx

from auth.email_domains import normalize_email
from auth.paths import (
    AUTH_CHECK_EMAIL,
    AUTH_LOGIN,
    AUTH_REGISTER,
    AUTH_TELEGRAM_LOGOUT,
    ME,
    USERS_LINK_TELEGRAM,
)
from bot.config import BACKEND_URL


class BackendError(Exception):
    """Raised when the booking backend returns an error or is unreachable."""

    def __init__(self, message: str, status_code: int = 0):
        """Store API error message and optional HTTP status."""
        self.status_code = status_code
        super().__init__(message)


class BackendClient:
    """HTTP client for booking API; auth uses same endpoints as the web SPA."""

    def __init__(self, telegram_id: int):
        self.telegram_id = telegram_id
        self._headers = {"X-Telegram-Id": str(telegram_id)}

    def _telegram_headers(self, telegram_username: str | None = None) -> dict[str, str]:
        headers = dict(self._headers)
        if telegram_username:
            headers["X-Telegram-Username"] = telegram_username
        return headers

    @staticmethod
    def _parse_error_detail(response: httpx.Response) -> str:
        detail = response.text.strip() or f"HTTP {response.status_code}"
        try:
            payload = response.json()
            raw = payload.get("detail", detail)
            if isinstance(raw, list):
                parts = []
                for item in raw:
                    if isinstance(item, dict):
                        parts.append(item.get("msg", str(item)))
                    else:
                        parts.append(str(item))
                detail = "; ".join(parts) or detail
            else:
                detail = str(raw)
        except Exception:
            pass
        return detail

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        auth: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        headers: dict[str, str] = dict(self._headers) if auth else {}
        if extra_headers:
            headers.update(extra_headers)
        url = f"{BACKEND_URL}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                response = await client.request(
                    method, url, json=json, params=params, headers=headers
                )
        except httpx.ConnectError:
            raise BackendError(
                f"не удалось подключиться к backend ({BACKEND_URL}). "
                "Проверьте, что сервис backend запущен."
            ) from None
        except httpx.HTTPError as exc:
            raise BackendError(f"ошибка сети при обращении к backend: {exc}") from None

        if response.status_code >= 400:
            detail = self._parse_error_detail(response)
            raise BackendError(detail, response.status_code)

        if response.status_code == 204:
            return None
        return response.json()

    async def check_email_exists(self, email: str) -> bool:
        """Return True when a registered web account exists for the email."""
        data = await self._request(
            "GET",
            AUTH_CHECK_EMAIL,
            params={"email": email.strip().lower()},
            auth=False,
        )
        return bool(data.get("exists"))

    async def login(
        self,
        email: str,
        password: str,
        *,
        telegram_username: str | None = None,
    ) -> dict:
        """Same as web login; binds Telegram when headers are set."""
        return await self._request(
            "POST",
            AUTH_LOGIN,
            json={"email": normalize_email(email), "password": password},
            auth=True,
            extra_headers=self._telegram_headers(telegram_username),
        )

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        *,
        telegram_username: str | None = None,
    ) -> dict:
        """Same as web register, then login to attach Telegram."""
        normalized = normalize_email(email)
        await self._request(
            "POST",
            AUTH_REGISTER,
            json={
                "email": normalized,
                "password": password,
                "full_name": full_name,
            },
            auth=False,
        )
        return await self.login(
            normalized, password, telegram_username=telegram_username
        )

    async def link_telegram(
        self,
        token: str,
        telegram_username: str | None = None,
    ) -> dict:
        """Bind Telegram via one-time token from the web app."""
        return await self._request(
            "POST",
            USERS_LINK_TELEGRAM,
            json={"token": token},
            auth=True,
            extra_headers=self._telegram_headers(telegram_username),
        )

    async def me(self) -> dict:
        """Current user profile (requires linked Telegram)."""
        return await self._request("GET", ME)

    async def unlink_telegram(self) -> dict:
        """Unlink Telegram from the web account (bot logout)."""
        return await self._request("POST", AUTH_TELEGRAM_LOGOUT)

    async def buildings(self) -> list:
        return await self._request("GET", "/api/v1/buildings")

    async def rooms(self, **filters) -> list:
        params = {k: v for k, v in filters.items() if v is not None}
        return await self._request("GET", "/api/v1/rooms", params=params)

    async def available_rooms(
        self, starts_at: str, ends_at: str, building_code: str | None = None
    ) -> list:
        params = {"starts_at": starts_at, "ends_at": ends_at}
        if building_code:
            params["building_code"] = building_code
        return await self._request("GET", "/api/v1/rooms/available", params=params)

    async def event_purposes(self) -> list:
        return await self._request("GET", "/api/v1/event-purposes")

    async def room_occupancy(self, room_id: int, date: str) -> list:
        return await self._request(
            "GET", f"/api/v1/rooms/{room_id}/occupancy", params={"date": date}
        )

    async def create_request(self, payload: dict) -> dict:
        return await self._request("POST", "/api/v1/booking-requests", json=payload)

    async def submit_request(self, request_id: str) -> dict:
        return await self._request(
            "POST", f"/api/v1/booking-requests/{request_id}/submit"
        )

    async def cancel_request(self, request_id: str) -> dict:
        return await self._request(
            "POST", f"/api/v1/booking-requests/{request_id}/cancel"
        )

    async def my_requests(self, scope: str = "active") -> list:
        return await self._request(
            "GET",
            "/api/v1/booking-requests/me",
            params={"scope": scope},
        )

    async def my_bookings(self, scope: str = "active") -> list:
        return await self._request("GET", "/api/v1/bookings/me", params={"scope": scope})

    async def cancel_booking(self, booking_id: str) -> dict:
        return await self._request("POST", f"/api/v1/bookings/{booking_id}/cancel")

    async def moderation_queue(self) -> list:
        return await self._request("GET", "/api/v1/moderation/requests")

    async def approve_request(self, request_id: str) -> dict:
        return await self._request(
            "POST", f"/api/v1/moderation/requests/{request_id}/approve"
        )

    async def reject_request(self, request_id: str, comment: str | None = None) -> dict:
        return await self._request(
            "POST",
            f"/api/v1/moderation/requests/{request_id}/reject",
            json={"comment": comment},
        )
