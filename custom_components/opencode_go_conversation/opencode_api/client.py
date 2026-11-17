"""High-level async client for the OpenCode Go model protocols."""

from __future__ import annotations

import re
from typing import AsyncIterator

import aiohttp

from .auth import AbstractAuth
from .errors import (
    OpenCodeGoApiError,
    OpenCodeGoError,
    OpenCodeGoModelNotInGo,
    OpenCodeGoRateLimited,
    OpenCodeGoServerOverloaded,
)
from .models import ResponseEvent
from .payloads import to_anthropic_body, to_chat_body, to_responses_body
from .requests import OpenCodeGoRequest
from .routing import (
    MODEL_CATALOG,
    MODEL_PREFIX,
    ModelCatalog,
    ModelRoute,
    normalize_model_id,
    resolve_model_route,
)
from .sse import anthropic_sse_iter, responses_sse_iter, sse_iter

RESPONSES_PATH = "/responses"
CHAT_COMPLETIONS_PATH = "/chat/completions"
ANTHROPIC_MESSAGES_PATH = "/messages"
MODELS_PATH = "/models"

_MODEL_NOT_IN_GO_RE = re.compile(
    r"modelnotingo|included in opencode go",
    re.IGNORECASE,
)

_STREAM_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}


class OpenCodeGoClient:
    """Async client for the OpenCode Go API."""

    def __init__(self, auth: AbstractAuth) -> None:
        self._auth = auth

    async def refresh_catalog(self) -> ModelCatalog:
        """Fetch the live model catalog and cache its endpoint routing."""
        resp = await self._auth.request("get", MODELS_PATH)
        try:
            await self._raise_for_status(resp)
            payload = await resp.json()
        finally:
            resp.release()

        MODEL_CATALOG.update(payload)
        return MODEL_CATALOG

    async def list_models(self, *, refresh: bool = False) -> list[str]:
        """Return the models published by the live OpenCode Go catalog.

        Pass ``refresh=True`` when filling a model picker: a cached catalog may
        be up to an hour old and can miss models OpenCode just published.
        """
        if refresh or not MODEL_CATALOG.is_fresh:
            await self.refresh_catalog()
        return [f"{MODEL_PREFIX}{model_id}" for model_id in MODEL_CATALOG.ids]

    async def _async_route(self, model: str) -> ModelRoute:
        """Return the route for *model*, refreshing the catalog on a miss."""
        model_id = normalize_model_id(model)
        route = MODEL_CATALOG.get(model_id)
        if route is None:
            await self.refresh_catalog()
            route = MODEL_CATALOG.get(model_id)
        if route is None:
            return resolve_model_route(model)
        return route

    async def _raise_for_status(self, resp: aiohttp.ClientResponse) -> None:
        """Translate an unsuccessful HTTP response into a typed error."""
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
            message = await resp.text()
            if _MODEL_NOT_IN_GO_RE.search(message):
                # The catalog is out of date: drop it so the next picker
                # refresh shows the models the plan actually includes.
                MODEL_CATALOG.invalidate()
                raise OpenCodeGoModelNotInGo(
                    "The selected model is not included in your OpenCode Go "
                    "plan anymore. Open the integration options and choose a "
                    "model from the refreshed list."
                )
            raise OpenCodeGoApiError(resp.status, message)

    async def stream(self, request: OpenCodeGoRequest) -> AsyncIterator[ResponseEvent]:
        """Submit *request* and stream back typed ``ResponseEvent`` objects."""
        session_id = request.session_id
        if not session_id:
            raise OpenCodeGoError(
                "OpenCode Go streaming requests require a stable session_id"
            )

        route = await self._async_route(request.model)
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
            await self._raise_for_status(resp)

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
