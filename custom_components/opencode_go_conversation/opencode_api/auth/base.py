"""API-key auth helper for OpenCode Go."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, cast

import aiohttp

DEFAULT_BASE_URL = "https://opencode.ai/zen/go/v1"
# OpenCode Go asks third-party clients to identify themselves with a specific
# user agent rather than relying on aiohttp's generic default.
OPENCODE_GO_USER_AGENT = "hass-opencode-go-conversation/0.2.0"


class AbstractAuth(ABC):
    """Abstract base class for OpenCode Go API authentication."""

    def __init__(
        self, session: aiohttp.ClientSession, base_url: str = DEFAULT_BASE_URL
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")

    @abstractmethod
    async def async_get_api_key(self) -> str:
        """Return the current API key."""

    async def request(
        self, method: str, path: str, **kwargs: object
    ) -> aiohttp.ClientResponse:
        """Make an authenticated request to the OpenCode Go API."""
        request_kwargs = cast(dict[str, Any], kwargs)
        raw_headers = cast(dict[str, str] | None, request_kwargs.pop("headers", None))
        headers = dict(raw_headers or {})
        header_names = {name.lower() for name in headers}
        if "authorization" not in header_names and "x-api-key" not in header_names:
            headers["Authorization"] = f"Bearer {await self.async_get_api_key()}"
        headers.setdefault("Accept", "application/json")
        headers["User-Agent"] = OPENCODE_GO_USER_AGENT
        return await self._session.request(
            method,
            f"{self._base_url}{path}",
            headers=headers,
            **request_kwargs,
        )


class OpenCodeGoAuth(AbstractAuth):
    """Concrete ``AbstractAuth`` backed by a static API key."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        super().__init__(session, base_url)
        self._api_key = api_key

    async def async_get_api_key(self) -> str:
        return self._api_key
