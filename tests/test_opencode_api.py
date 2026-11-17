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
    OpenCodeGoModelNotInGo,
    OpenCodeGoRequest,
)
from custom_components.opencode_go_conversation.opencode_api.models import (
    FunctionCallArgumentsDone,
    OutputTextDelta,
)
from custom_components.opencode_go_conversation.opencode_api.routing import (
    MODEL_CATALOG,
    ModelRoute,
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
        model="opencode-go/deepseek-v4.1-flash",
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
                    model="opencode-go/deepseek-v4.1-flash",
                    messages=[],
                )
            )
        ]


@pytest.mark.asyncio
async def test_stream_rejects_models_missing_from_the_catalog() -> None:
    auth = _CatalogAuth(CATALOG_PAYLOAD)
    client = OpenCodeGoClient(cast(AbstractAuth, auth))

    with pytest.raises(OpenCodeGoModelNotInGo, match="current OpenCode Go catalog"):
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
    assert ("get", "/models") in auth.requests


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "path", "protocol"),
    [
        ("opencode-go/gpt-5.6-luna", "/responses", "responses"),
        ("opencode-go/deepseek-v4.1-flash", "/chat/completions", "chat"),
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


class _CatalogResponse(_FakeResponse):
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    async def json(self) -> dict[str, Any]:
        return self._payload


class _CatalogAuth(_FakeAuth):
    """Serve the model catalog for ``GET /models`` and the fake stream otherwise."""

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__()
        self.payload = payload
        self.requests: list[tuple[str, str]] = []

    async def request(self, method: str, path: str, **kwargs: object) -> _FakeResponse:
        self.requests.append((method, path))
        if path == "/models":
            return _CatalogResponse(self.payload)
        return await super().request(method, path, **kwargs)


CATALOG_PAYLOAD: dict[str, Any] = {
    "data": [
        {"id": "deepseek-v4.1-flash", "api": {"chat-completions": {}}},
        {"id": "gpt-6-luna", "api": {"responses": {}}},
        {"id": "qwen4-max", "api": {"messages": {}}},
        {"id": "gemini-4-argon", "api": {"generate-content": {}}},
        {"id": "no-api-metadata"},
    ]
}


@pytest.mark.asyncio
async def test_list_models_returns_the_live_catalog_routes() -> None:
    MODEL_CATALOG.reset()
    auth = _CatalogAuth(CATALOG_PAYLOAD)

    models = await OpenCodeGoClient(cast(AbstractAuth, auth)).list_models()

    assert models == [
        "opencode-go/deepseek-v4.1-flash",
        "opencode-go/gpt-6-luna",
        "opencode-go/qwen4-max",
    ]
    assert MODEL_CATALOG.get("gpt-6-luna") == ModelRoute(
        "gpt-6-luna", "responses", "/responses"
    )


@pytest.mark.asyncio
async def test_stream_routes_a_model_discovered_at_runtime() -> None:
    MODEL_CATALOG.reset()
    auth = _CatalogAuth(
        {
            "data": [
                {"id": "brand-new-model", "api": {"chat-completions": {}}},
            ]
        }
    )
    client = OpenCodeGoClient(cast(AbstractAuth, auth))

    _ = [
        event
        async for event in client.stream(
            OpenCodeGoRequest(
                model="opencode-go/brand-new-model",
                messages=[],
                session_id="conversation-1",
            )
        )
    ]

    assert ("get", "/models") in auth.requests
    assert auth.path == "/chat/completions"
    assert auth.body is not None
    assert auth.body["model"] == "brand-new-model"


@pytest.mark.asyncio
async def test_stream_reports_models_dropped_from_the_plan() -> None:
    class NotInGoResponse(_FakeResponse):
        status = 400

        async def text(self) -> str:
            return (
                '{"error":{"type":"server_error","message":"Model '
                "deepseek-v4.1-flash isn't included in OpenCode Go."
                '"}}'
            )

    class NotInGoAuth(_FakeAuth):
        async def request(
            self, method: str, path: str, **kwargs: object
        ) -> NotInGoResponse:
            return NotInGoResponse()

    client = OpenCodeGoClient(cast(AbstractAuth, NotInGoAuth()))

    with pytest.raises(OpenCodeGoModelNotInGo, match="not included"):
        _ = [
            event
            async for event in client.stream(
                OpenCodeGoRequest(
                    model="opencode-go/deepseek-v4.1-flash",
                    messages=[],
                    session_id="conversation-1",
                )
            )
        ]

    assert MODEL_CATALOG.is_fresh is False


@pytest.mark.asyncio
async def test_catalog_rejects_unexpected_payloads() -> None:
    with pytest.raises(OpenCodeGoError, match="unexpected model catalog"):
        MODEL_CATALOG.update({"data": "nope"})


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
