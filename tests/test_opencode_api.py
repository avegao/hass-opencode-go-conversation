"""Tests for the OpenCode Go HTTP client contract."""

from __future__ import annotations

from typing import Any, cast

import aiohttp
import pytest

from custom_components.opencode_go_conversation.opencode_api import (
    OPENCODE_GO_USER_AGENT,
    AbstractAuth,
    OpenCodeGoAuth,
    OpenCodeGoClient,
    OpenCodeGoError,
    OpenCodeGoRequest,
)


class _FakeSession:
    """Capture requests made by the authentication helper."""

    def __init__(self) -> None:
        self.request_args: tuple[Any, ...] | None = None
        self.request_kwargs: dict[str, Any] | None = None

    async def request(self, *args: Any, **kwargs: Any) -> object:
        self.request_args = args
        self.request_kwargs = kwargs
        return object()


@pytest.mark.asyncio
async def test_auth_identifies_the_integration() -> None:
    session = _FakeSession()
    auth = OpenCodeGoAuth(
        cast(aiohttp.ClientSession, session),
        "test-api-key",
    )

    await auth.request("get", "/models", headers={"User-Agent": "python"})

    assert session.request_kwargs is not None
    headers = session.request_kwargs["headers"]
    assert headers["Authorization"] == "Bearer test-api-key"
    assert headers["User-Agent"] == OPENCODE_GO_USER_AGENT


class _EmptyContent:
    def __aiter__(self) -> _EmptyContent:
        return self

    async def __anext__(self) -> bytes:
        raise StopAsyncIteration


class _FakeResponse:
    status = 200
    headers: dict[str, str] = {}
    content = _EmptyContent()

    def release(self) -> None:
        """Match the aiohttp response interface used by the client."""


class _FakeAuth:
    def __init__(self) -> None:
        self.headers: dict[str, str] | None = None

    async def request(self, method: str, path: str, **kwargs: object) -> _FakeResponse:
        self.headers = cast(dict[str, str], kwargs["headers"])
        return _FakeResponse()


@pytest.mark.asyncio
async def test_stream_sends_the_per_conversation_session_header() -> None:
    auth = _FakeAuth()
    client = OpenCodeGoClient(cast(AbstractAuth, auth))
    request = OpenCodeGoRequest(
        model="opencode-go/deepseek-v4-flash",
        messages=[],
        session_id="ha-conversation-123",
    )

    events = [event async for event in client.stream(request)]

    assert events == []
    assert auth.headers is not None
    assert auth.headers["x-opencode-session"] == "ha-conversation-123"


@pytest.mark.asyncio
async def test_stream_rejects_requests_without_a_session_id() -> None:
    client = OpenCodeGoClient(cast(AbstractAuth, _FakeAuth()))

    with pytest.raises(OpenCodeGoError, match="stable session_id"):
        _ = [
            event
            async for event in client.stream(
                OpenCodeGoRequest(
                    model="opencode-go/deepseek-v4-flash",
                    messages=[],
                )
            )
        ]
