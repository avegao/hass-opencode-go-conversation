"""
OpenCodeGoClient — high-level async client for the OpenCode Go Responses API.
"""

from __future__ import annotations

from typing import AsyncIterator

from .auth import AbstractAuth
from .errors import (
    OpenCodeGoApiError,
    OpenCodeGoRateLimited,
    OpenCodeGoServerOverloaded,
)
from .models import ResponseEvent
from .requests import OpenCodeGoRequest
from .sse import sse_iter

RESPONSES_PATH = "/responses"
CHAT_COMPLETIONS_PATH = "/chat/completions"
MODELS_PATH = "/models"

_STREAM_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}


class OpenCodeGoClient:
    """Async client for the OpenCode Go API."""

    def __init__(self, auth: AbstractAuth) -> None:
        self._auth = auth

    async def list_models(self) -> list[str]:
        """Return the configured Go models as `opencode-go/<id>` strings."""
        resp = await self._auth.request("get", MODELS_PATH)
        try:
            if resp.status == 401:
                raise OpenCodeGoApiError(401, "Unauthorized — API key is invalid")
            if resp.status == 429:
                retry_after: float | None = None
                ra = resp.headers.get("Retry-After")
                if ra and ra.isdigit():
                    retry_after = float(ra)
                raise OpenCodeGoRateLimited(await resp.text(), retry_after=retry_after)
            if resp.status == 503:
                raise OpenCodeGoServerOverloaded(await resp.text())
            if resp.status >= 400:
                raise OpenCodeGoApiError(resp.status, await resp.text())

            payload = await resp.json()
            models = payload.get("data", []) if isinstance(payload, dict) else []
            return [
                f"opencode-go/{item['id']}"
                for item in models
                if isinstance(item, dict) and item.get("id")
            ]
        finally:
            resp.release()

    async def stream(self, request: OpenCodeGoRequest) -> AsyncIterator[ResponseEvent]:
        """Submit *request* and stream back typed ``ResponseEvent`` objects."""
        resp = await self._auth.request(
            "post",
            CHAT_COMPLETIONS_PATH,
            headers=_STREAM_HEADERS,
            json=request.to_body(),
        )
        try:
            if resp.status == 401:
                raise OpenCodeGoApiError(401, "Unauthorized — API key is invalid")
            if resp.status == 429:
                retry_after: float | None = None
                ra = resp.headers.get("Retry-After")
                if ra and ra.isdigit():
                    retry_after = float(ra)
                raise OpenCodeGoRateLimited(await resp.text(), retry_after=retry_after)
            if resp.status == 503:
                raise OpenCodeGoServerOverloaded(await resp.text())
            if resp.status >= 400:
                raise OpenCodeGoApiError(resp.status, await resp.text())

            async for event in sse_iter(resp):
                yield event
        finally:
            resp.release()
