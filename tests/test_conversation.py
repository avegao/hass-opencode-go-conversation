"""Tests for the conversation entity and helper functions."""

from __future__ import annotations

from datetime import date, datetime
import json
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

from homeassistant.components.conversation import (
    AssistantContent,
    AssistantContentDeltaDict,
    SystemContent,
    ToolResultContent,
    UserContent,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
import pytest

from custom_components.opencode_go_conversation.conversation import (
    MAX_TOOL_ITERATIONS,
    _events_to_deltas,
    async_run_chat_log,
)
from custom_components.opencode_go_conversation.opencode_api import (
    FunctionCallAdded,
    FunctionCallArgumentsDone,
    OpenCodeGoClient,
    OpenCodeGoRequest,
    OutputTextDelta,
)
from custom_components.opencode_go_conversation.transform import (
    build_chat_messages,
    build_input_items,
    extract_instructions,
    json_default,
)

from .conftest import make_chat_log


def test_extract_instructions_returns_system_content():
    chat_log = make_chat_log(
        [
            SystemContent(content="You are helpful."),
            UserContent(content="Hi"),
        ]
    )
    assert extract_instructions(chat_log) == "You are helpful."


@pytest.mark.asyncio
async def test_build_input_items_user_message():
    chat_log = make_chat_log([UserContent(content="Hello")])
    items = build_input_items(chat_log)

    assert len(items) == 1
    assert items[0] == {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "Hello"}],
    }


@pytest.mark.asyncio
async def test_build_input_items_tool_result():
    chat_log = make_chat_log(
        [
            ToolResultContent(
                agent_id="conversation.opencode_go_conversation",
                tool_call_id="call_1",
                tool_name="turn_on",
                tool_result={"success": True},
            ),
        ]
    )
    items = build_input_items(chat_log)

    assert len(items) == 1
    assert items[0]["type"] == "function_call_output"
    assert items[0]["call_id"] == "call_1"
    assert json.loads(items[0]["output"]) == {"success": True}


@pytest.mark.asyncio
async def test_build_chat_messages_preserves_text_and_tool_calls():
    tool_call = type(
        "ToolCall",
        (),
        {
            "id": "call_1",
            "tool_name": "turn_on",
            "tool_args": {"entity_id": "light.kitchen"},
        },
    )()
    chat_log = make_chat_log(
        [
            SystemContent(content="You are helpful."),
            UserContent(content="Hello"),
            AssistantContent(
                agent_id="conversation.opencode_go_conversation",
                content="Turning on the light.",
                tool_calls=[cast(Any, tool_call)],
            ),
            ToolResultContent(
                agent_id="conversation.opencode_go_conversation",
                tool_call_id="call_1",
                tool_name="turn_on",
                tool_result={"success": True},
            ),
        ]
    )

    messages = build_chat_messages(chat_log, system_prompt="You are helpful.")

    assert messages[0] == {"role": "system", "content": "You are helpful."}
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[2]["tool_calls"][0]["function"]["name"] == "turn_on"
    assert messages[3]["role"] == "tool"
    assert json.loads(messages[3]["content"]) == {"success": True}


@pytest.mark.asyncio
async def test_events_to_deltas_emits_text_and_tool_calls():
    request = OpenCodeGoRequest(
        model="opencode-go/kimi-k3",
        messages=[],
    )

    class FakeClient:
        async def stream(self, request):
            yield OutputTextDelta(delta="Hello", content_index=0)
            yield FunctionCallAdded(call_id="call_1", name="turn_on", item_id="item_1")
            yield FunctionCallArgumentsDone(
                arguments='{"entity_id":"light.kitchen"}', item_id="item_1"
            )

    deltas: list[AssistantContentDeltaDict] = []
    client = cast(OpenCodeGoClient, FakeClient())
    async for delta in _events_to_deltas(client, request):
        deltas.append(delta)

    assert deltas[0] == {"role": "assistant"}
    assert deltas[1] == {"content": "Hello"}
    tool_call_delta = deltas[2]
    tool_calls = cast(Any, tool_call_delta["tool_calls"])
    assert tool_calls[0].tool_name == "turn_on"
    assert tool_calls[0].tool_args == {"entity_id": "light.kitchen"}


@pytest.mark.asyncio
async def test_async_run_chat_log_appends_final_assistant_content():
    chat_log = make_chat_log([UserContent(content="Hello")])
    requests: list[OpenCodeGoRequest] = []

    class FakeClient:
        async def stream(self, request):
            requests.append(request)
            yield OutputTextDelta(delta="Result text", content_index=0)

    await async_run_chat_log(
        chat_log=chat_log,
        client=cast(OpenCodeGoClient, FakeClient()),
        model="opencode-go/kimi-k3",
        entity_id="conversation.opencode_go_conversation",
        reasoning_effort="medium",
        reasoning_summary="off",
        text_verbosity="medium",
    )

    assert isinstance(chat_log.content[-1], AssistantContent)
    assert chat_log.content[-1].content == "Result text"
    assert requests[0].session_id == chat_log.conversation_id


@pytest.mark.asyncio
async def test_async_run_chat_log_rejects_missing_conversation_id():
    chat_log = make_chat_log([UserContent(content="Hello")])
    chat_log.conversation_id = ""

    class FakeClient:
        async def stream(self, request):
            raise AssertionError("provider must not receive a request")
            yield

    with pytest.raises(HomeAssistantError, match="stable.*conversation ID"):
        await async_run_chat_log(
            chat_log=chat_log,
            client=cast(OpenCodeGoClient, FakeClient()),
            model="opencode-go/kimi-k3",
            entity_id="conversation.opencode_go_conversation",
            reasoning_effort="medium",
            reasoning_summary="off",
            text_verbosity="medium",
        )


@pytest.mark.asyncio
async def test_async_run_chat_log_caps_tool_iterations():
    chat_log = make_chat_log([UserContent(content="Hello")], unresponded=True)
    requests: list[OpenCodeGoRequest] = []

    class FakeClient:
        async def stream(self, request):
            requests.append(request)
            yield OutputTextDelta(delta="Result text", content_index=0)

    await async_run_chat_log(
        chat_log=chat_log,
        client=cast(OpenCodeGoClient, FakeClient()),
        model="opencode-go/kimi-k3",
        entity_id="conversation.opencode_go_conversation",
        reasoning_effort="medium",
        reasoning_summary="off",
        text_verbosity="medium",
        max_iterations=100,
    )

    assert len(requests) == MAX_TOOL_ITERATIONS


@pytest.mark.asyncio
async def test_async_run_chat_log_passes_custom_serializer_to_tool_formatter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forward HA's selector serializer to the schema converter."""
    import custom_components.opencode_go_conversation.conversation as conversation

    def serializer(schema: object) -> dict[str, str]:
        return {"type": "string"}

    tool = MagicMock(spec=llm.Tool)
    llm_api = SimpleNamespace(tools=[tool], custom_serializer=serializer, api_prompt="")
    chat_log = make_chat_log([UserContent(content="Hello")], llm_api=llm_api)
    calls: list[tuple[object, object]] = []

    def fake_format_tool(tool: object, *, custom_serializer: object) -> dict[str, Any]:
        calls.append((tool, custom_serializer))
        return {"type": "function"}

    monkeypatch.setattr(conversation, "format_tool", fake_format_tool)

    class FakeClient:
        async def stream(self, request):
            yield OutputTextDelta(delta="Result text", content_index=0)

    await async_run_chat_log(
        chat_log=chat_log,
        client=cast(OpenCodeGoClient, FakeClient()),
        model="opencode-go/kimi-k3",
        entity_id="conversation.opencode_go_conversation",
        reasoning_effort="medium",
        reasoning_summary="off",
        text_verbosity="medium",
    )

    assert calls == [(tool, serializer)]


@pytest.mark.asyncio
async def test_async_run_chat_log_without_no_entities_prompt_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Support Home Assistant versions without the legacy prompt constant."""
    monkeypatch.delattr(llm, "NO_ENTITIES_PROMPT", raising=False)
    chat_log = make_chat_log(
        [UserContent(content="Hello")],
        llm_api=SimpleNamespace(tools=[], custom_serializer=None, api_prompt=""),
    )

    class FakeClient:
        async def stream(self, request):
            yield OutputTextDelta(delta="Result text", content_index=0)

    await async_run_chat_log(
        chat_log=chat_log,
        client=cast(OpenCodeGoClient, FakeClient()),
        model="opencode-go/kimi-k3",
        entity_id="conversation.opencode_go_conversation",
        reasoning_effort="medium",
        reasoning_summary="off",
        text_verbosity="medium",
    )


def test_json_default_date_and_datetime():
    assert json_default(date(2026, 3, 3)) == "2026-03-03"
    assert json_default(datetime(2026, 3, 3, 15, 0, 0)) == "2026-03-03T15:00:00"
