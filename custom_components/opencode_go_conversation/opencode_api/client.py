"""High-level async client for the OpenCode Go model protocols."""

from __future__ import annotations

from typing import AsyncIterator

from .auth import AbstractAuth
from .errors import (
    OpenCodeGoApiError,
    OpenCodeGoError,
    OpenCodeGoRateLimited,
    OpenCodeGoServerOverloaded,
)
from .models import ResponseEvent
from .payloads import to_anthropic_body, to_chat_body, to_responses_body
from .requests import OpenCodeGoRequest
from .routing import MODEL_PREFIX, resolve_model_route
from .sse import anthropic_sse_iter, responses_sse_iter, sse_iter

RESPONSES_PATH = "/responses"
CHAT_COMPLETIONS_PATH = "/chat/completions"
ANTHROPIC_MESSAGES_PATH = "/messages"
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
            result: list[str] = []
            for item in models:
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                try:
                    route = resolve_model_route(str(item["id"]))
                except OpenCodeGoError:
                    # The catalog can contain models that are not in the
                    # documented endpoint table yet.  Do not expose a model
                    # that this client cannot serialise and stream safely.
                    continue
                result.append(f"{MODEL_PREFIX}{route.model_id}")
            return result
        finally:
            resp.release()

    async def stream(self, request: OpenCodeGoRequest) -> AsyncIterator[ResponseEvent]:
        """Submit *request* and stream back typed ``ResponseEvent`` objects."""
        session_id = request.session_id
        if not session_id:
            raise OpenCodeGoError(
                "OpenCode Go streaming requests require a stable session_id"
            )

        route = resolve_model_route(request.model)
        headers = dict(_STREAM_HEADERS)
        headers["x-opencode-session"] = session_id
        if route.protocol == "anthropic":
            headers["x-api-key"] = await self._auth.async_get_api_key()
            headers["anthropic-version"] = "2023-06-01"

        if route.protocol == "responses":
            body = to_responses_body(request)
        elif route.protocol == "anthropic":
            body = to_anthropic_body(request)
        else:
            body = to_chat_body(request)

        resp = await self._auth.request(
            "post",
            route.path,
            headers=headers,
            json=body,
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

            if route.protocol == "responses":
                event_stream = responses_sse_iter(resp)
            elif route.protocol == "anthropic":
                event_stream = anthropic_sse_iter(resp)
            else:
                event_stream = sse_iter(resp)
            async for event in event_stream:
                yield event
        finally:
            resp.release()
