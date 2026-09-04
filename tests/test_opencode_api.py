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
from custom_components.opencode_go_conversation.opencode_api.models import (
    FunctionCallArgumentsDone,
    OutputTextDelta,
)
from custom_components.opencode_go_conversation.opencode_api.sse import (
    anthropic_sse_iter,
    responses_sse_iter,
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


@pytest.mark.asyncio
async def test_auth_preserves_anthropic_api_key_header_without_bearer() -> None:
    session = _FakeSession()
    auth = OpenCodeGoAuth(
        cast(aiohttp.ClientSession, session),
        "test-api-key",
    )

    await auth.request(
        "post",
        "/messages",
        headers={
            "x-api-key": "test-api-key",
            "anthropic-version": "2023-06-01",
        },
    )

    assert session.request_kwargs is not None
    headers = session.request_kwargs["headers"]
    assert headers["x-api-key"] == "test-api-key"
    assert "Authorization" not in headers


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
        self.path: str | None = None
        self.body: dict[str, Any] | None = None

    async def async_get_api_key(self) -> str:
        return "test-api-key"

    async def request(self, method: str, path: str, **kwargs: object) -> _FakeResponse:
        self.headers = cast(dict[str, str], kwargs["headers"])
        self.path = path
        self.body = cast(dict[str, Any], kwargs.get("json"))
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


@pytest.mark.asyncio
async def test_stream_rejects_models_without_a_documented_route() -> None:
    auth = _FakeAuth()
    client = OpenCodeGoClient(cast(AbstractAuth, auth))

    with pytest.raises(OpenCodeGoError, match="known endpoint mapping"):
        _ = [
            event
            async for event in client.stream(
                OpenCodeGoRequest(
                    model="opencode-go/not-yet-documented",
                    messages=[],
                    session_id="conversation-1",
                )
            )
        ]

    assert auth.path is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "path", "protocol"),
    [
        ("opencode-go/gpt-5.6-luna", "/responses", "responses"),
        ("opencode-go/deepseek-v4-flash", "/chat/completions", "chat"),
        ("opencode-go/qwen3.8-max", "/messages", "anthropic"),
    ],
)
async def test_stream_routes_model_to_documented_protocol(
    model: str, path: str, protocol: str
) -> None:
    auth = _FakeAuth()
    client = OpenCodeGoClient(cast(AbstractAuth, auth))
    request = OpenCodeGoRequest(
        model=model,
        messages=[
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Hello"},
        ],
        instructions="Be concise.",
        input_items=[
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Hello"}],
            }
        ],
        session_id="conversation-1",
    )

    _ = [event async for event in client.stream(request)]

    assert auth.path == path
    assert auth.body is not None
    assert auth.body["model"] == model.removeprefix("opencode-go/")
    assert auth.headers is not None
    assert auth.headers["x-opencode-session"] == "conversation-1"
    if protocol == "anthropic":
        assert auth.headers["x-api-key"] == "test-api-key"
        assert "Authorization" not in auth.headers
        assert auth.body["system"] == "Be concise."
        assert auth.body["messages"][0]["role"] == "user"
    elif protocol == "responses":
        assert auth.body["input"] == request.input_items
        assert auth.body["instructions"] == "Be concise."
    else:
        assert auth.body["messages"][0]["role"] == "system"


@pytest.mark.asyncio
async def test_list_models_hides_catalog_models_without_a_route() -> None:
    class CatalogResponse(_FakeResponse):
        async def json(self) -> dict[str, Any]:
            return {
                "data": [
                    {"id": "deepseek-v4-flash"},
                    {"id": "not-yet-documented"},
                ]
            }

    class CatalogAuth(_FakeAuth):
        async def request(
            self, method: str, path: str, **kwargs: object
        ) -> CatalogResponse:
            return CatalogResponse()

    models = await OpenCodeGoClient(cast(AbstractAuth, CatalogAuth())).list_models()

    assert models == ["opencode-go/deepseek-v4-flash"]


class _LinesContent:
    def __init__(self, text: str) -> None:
        self._lines = [line.encode() for line in text.splitlines()]

    def __aiter__(self) -> _LinesContent:
        return self

    async def __anext__(self) -> bytes:
        if not self._lines:
            raise StopAsyncIteration
        return self._lines.pop(0)


@pytest.mark.asyncio
async def test_responses_sse_translates_text_and_tool_arguments() -> None:
    response = cast(
        aiohttp.ClientResponse,
        type(
            "Response",
            (),
            {
                "content": _LinesContent(
                    "\n".join(
                        [
                            "event: response.output_text.delta",
                            'data: {"type":"response.output_text.delta","delta":"Hi"}',
                            "",
                            "event: response.output_item.added",
                            'data: {"type":"response.output_item.added","item":{"id":"fc_1","type":"function_call","call_id":"call_1","name":"turn_on"}}',
                            "",
                            "event: response.function_call_arguments.done",
                            'data: {"type":"response.function_call_arguments.done","item_id":"fc_1","arguments":"{}"}',
                            "",
                        ]
                    )
                )
            },
        )(),
    )

    events = [event async for event in responses_sse_iter(response)]

    assert OutputTextDelta(delta="Hi", content_index=0) in events
    assert FunctionCallArgumentsDone(arguments="{}", item_id="fc_1") in events


@pytest.mark.asyncio
async def test_anthropic_sse_translates_text_and_tool_arguments() -> None:
    response = cast(
        aiohttp.ClientResponse,
        type(
            "Response",
            (),
            {
                "content": _LinesContent(
                    "\n".join(
                        [
                            "event: content_block_delta",
                            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}',
                            "",
                            "event: content_block_start",
                            'data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"call_1","name":"turn_on"}}',
                            "",
                            "event: content_block_delta",
                            'data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{}"}}',
                            "",
                            "event: content_block_stop",
                            'data: {"type":"content_block_stop","index":1}',
                            "",
                            "event: message_stop",
                            'data: {"type":"message_stop"}',
                            "",
                        ]
                    )
                )
            },
        )(),
    )

    events = [event async for event in anthropic_sse_iter(response)]

    assert OutputTextDelta(delta="Hi", content_index=0) in events
    assert FunctionCallArgumentsDone(arguments="{}", item_id="call_1") in events
