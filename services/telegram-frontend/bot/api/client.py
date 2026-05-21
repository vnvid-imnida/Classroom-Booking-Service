# Uses PEP 8
# Tools: black, flake8, mypy

from typing import Any

import httpx

from bot.config import BACKEND_URL


class BackendError(Exception):
    """Raised when the booking backend returns an error or is unreachable."""

    def __init__(self, message: str, status_code: int = 0):
        """Store API error message and optional HTTP status.

        Args:
            message: Human-readable error detail.
            status_code: HTTP status when the response was received.
        """
        self.status_code = status_code
        super().__init__(message)


class BackendClient:
    """Async HTTP client for the booking backend scoped to one Telegram user."""

    def __init__(self, telegram_id: int):
        """Bind requests to a Telegram user via ``X-Telegram-Id`` header.

        Args:
            telegram_id: Telegram user id used for authentication.
        """
        self.telegram_id = telegram_id
        self._headers = {"X-Telegram-Id": str(telegram_id)}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        auth: bool = True,
    ) -> Any:
        """Perform an HTTP request against the backend API.

        Args:
            method: HTTP verb (GET, POST, ...).
            path: API path starting with ``/api/``.
            json: Optional JSON request body.
            params: Optional query parameters.
            auth: When False, omit Telegram auth headers.

        Returns:
            Parsed JSON body, or None for 204 responses.

        Raises:
            BackendError: On network failure or HTTP status >= 400.
        """
        headers = self._headers if auth else {}
        url = f"{BACKEND_URL}{path}"
        try:
            # trust_env=False — не ходить на backend через HTTP_PROXY (даёт ложный 503 на localhost)
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                response = await client.request(method, url, json=json, params=params, headers=headers)
        except httpx.ConnectError:
            raise BackendError(
                f"не удалось подключиться к backend ({BACKEND_URL}). "
                "Проверьте, что сервис backend запущен."
            ) from None
        except httpx.HTTPError as exc:
            raise BackendError(f"ошибка сети при обращении к backend: {exc}") from None

        if response.status_code >= 400:
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
            if response.status_code == 404 and "register" in path:
                detail = (
                    f"{detail}. Возможно, backend не обновлён — пересоберите: "
                    "docker compose build backend && docker compose up -d backend"
                )
            raise BackendError(detail, response.status_code)

        if response.status_code == 204:
            return None
        return response.json()

    async def check_email_exists(self, email: str) -> bool:
        """Return True when a registered web account exists for the email."""
        data = await self._request(
            "GET",
            "/api/v1/auth/check-email",
            params={"email": email.strip().lower()},
            auth=False,
        )
        return bool(data.get("exists"))

    async def web_login(
        self,
        email: str,
        password: str,
        *,
        telegram_username: str | None = None,
    ) -> dict:
        """Log in with email/password and link Telegram in one request.

        Args:
            email: Registered web account email.
            password: Account password.
            telegram_username: Optional ``@username`` for the link.

        Returns:
            Auth payload with ``access_token`` and ``user``.

        Raises:
            BackendError: On invalid credentials or link conflicts.
        """
        headers = {"X-Telegram-Id": str(self.telegram_id)}
        if telegram_username:
            headers["X-Telegram-Username"] = telegram_username
        url = f"{BACKEND_URL}/api/v1/auth/login"
        try:
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                response = await client.post(
                    url,
                    json={"email": email, "password": password},
                    headers=headers,
                )
        except httpx.ConnectError:
            raise BackendError(
                f"не удалось подключиться к backend ({BACKEND_URL}). "
                "Проверьте, что сервис backend запущен."
            ) from None
        except httpx.HTTPError as exc:
            raise BackendError(f"ошибка сети при обращении к backend: {exc}") from None

        if response.status_code >= 400:
            detail = response.text.strip() or f"HTTP {response.status_code}"
            try:
                payload = response.json()
                detail = str(payload.get("detail", detail))
            except Exception:
                pass
            raise BackendError(detail, response.status_code)
        return response.json()

    async def link_telegram(
        self,
        token: str,
        telegram_username: str | None = None,
    ) -> dict:
        """Consume a web-generated link token and bind this Telegram account.

        Args:
            token: One-time token from ``/start link_<token>``.
            telegram_username: Optional ``@username`` for storage.

        Returns:
            Updated user profile dict.

        Raises:
            BackendError: When the token is invalid or expired.
        """
        headers = {
            "X-Telegram-Id": str(self.telegram_id),
        }
        if telegram_username:
            headers["X-Telegram-Username"] = telegram_username
        url = f"{BACKEND_URL}/api/v1/users/link-telegram"
        try:
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                response = await client.post(
                    url,
                    json={"token": token},
                    headers=headers,
                )
        except httpx.ConnectError:
            raise BackendError(
                f"не удалось подключиться к backend ({BACKEND_URL}). "
                "Проверьте, что сервис backend запущен."
            ) from None
        except httpx.HTTPError as exc:
            raise BackendError(f"ошибка сети при обращении к backend: {exc}") from None

        if response.status_code >= 400:
            detail = response.text.strip() or f"HTTP {response.status_code}"
            try:
                payload = response.json()
                detail = str(payload.get("detail", detail))
            except Exception:
                pass
            raise BackendError(detail, response.status_code)
        return response.json()

    async def register(self, telegram_username: str | None, full_name: str) -> dict:
        """Legacy Telegram-only registration (no web email).

        Args:
            telegram_username: Optional Telegram handle.
            full_name: Display name stored in the backend.

        Returns:
            Created or updated user dict.
        """
        payload: dict = {
            "telegram_id": self.telegram_id,
            "full_name": full_name,
        }
        if telegram_username:
            payload["telegram_username"] = telegram_username
        return await self._request(
            "POST",
            "/api/v1/users/register",
            json=payload,
            auth=False,
        )

    async def me(self) -> dict:
        """Fetch the current user profile for this Telegram id."""
        return await self._request("GET", "/api/v1/me")

    async def unlink_telegram(self) -> dict:
        """Unlink Telegram from the web account (bot logout)."""
        return await self._request("POST", "/api/v1/auth/telegram-logout")

    async def buildings(self) -> list:
        """List all campus buildings."""
        return await self._request("GET", "/api/v1/buildings")

    async def rooms(self, **filters) -> list:
        """Search rooms with optional query filters passed as kwargs."""
        params = {k: v for k, v in filters.items() if v is not None}
        return await self._request("GET", "/api/v1/rooms", params=params)

    async def available_rooms(
        self, starts_at: str, ends_at: str, building_code: str | None = None
    ) -> list:
        """List rooms free between two ISO datetimes."""
        params = {"starts_at": starts_at, "ends_at": ends_at}
        if building_code:
            params["building_code"] = building_code
        return await self._request("GET", "/api/v1/rooms/available", params=params)

    async def event_purposes(self) -> list:
        """List active event purpose options."""
        return await self._request("GET", "/api/v1/event-purposes")

    async def room_occupancy(self, room_id: int, date: str) -> list:
        """Return occupancy slots for one room on a calendar day."""
        return await self._request(
            "GET", f"/api/v1/rooms/{room_id}/occupancy", params={"date": date}
        )

    async def create_request(self, payload: dict) -> dict:
        """Create a draft booking request."""
        return await self._request("POST", "/api/v1/booking-requests", json=payload)

    async def submit_request(self, request_id: str) -> dict:
        """Submit a draft request for moderation."""
        return await self._request("POST", f"/api/v1/booking-requests/{request_id}/submit")

    async def cancel_request(self, request_id: str) -> dict:
        """Cancel a draft or pending request."""
        return await self._request("POST", f"/api/v1/booking-requests/{request_id}/cancel")

    async def my_requests(self, scope: str = "active") -> list:
        """List the user's booking requests (active or archive)."""
        return await self._request(
            "GET",
            "/api/v1/booking-requests/me",
            params={"scope": scope},
        )

    async def my_bookings(self, scope: str = "active") -> list:
        """List the user's confirmed bookings (active or archive)."""
        return await self._request("GET", "/api/v1/bookings/me", params={"scope": scope})

    async def cancel_booking(self, booking_id: str) -> dict:
        """Cancel an active booking owned by the user."""
        return await self._request("POST", f"/api/v1/bookings/{booking_id}/cancel")

    async def moderation_queue(self) -> list:
        """List pending requests awaiting moderator action."""
        return await self._request("GET", "/api/v1/moderation/requests")

    async def approve_request(self, request_id: str) -> dict:
        """Approve a pending request and create a booking."""
        return await self._request("POST", f"/api/v1/moderation/requests/{request_id}/approve")

    async def reject_request(self, request_id: str, comment: str | None = None) -> dict:
        """Reject a pending request with an optional comment."""
        return await self._request(
            "POST",
            f"/api/v1/moderation/requests/{request_id}/reject",
            json={"comment": comment},
        )
