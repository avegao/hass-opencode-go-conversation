"""Tests for the conversation entity and helper functions."""

from __future__ import annotations

from datetime import date, datetime
import json

from homeassistant.components.conversation import (
    AssistantContent,
    SystemContent,
    ToolResultContent,
    UserContent,
)
import pytest

from custom_components.opencode_go_conversation.conversation import (
    _events_to_deltas,
    async_run_chat_log,
)
from custom_components.opencode_go_conversation.opencode_api import (
    FunctionCallAdded,
    FunctionCallArgumentsDone,
    OpenCodeGoRequest,
    OutputTextDelta,
)
from custom_components.opencode_go_conversation.transform import (
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
async def test_events_to_deltas_emits_text_and_tool_calls():
    request = OpenCodeGoRequest(
        model="opencode-go/kimi-k3",
        input=[],
    )

    class FakeClient:
        async def stream(self, request):
            yield OutputTextDelta(delta="Hello", content_index=0)
            yield FunctionCallAdded(call_id="call_1", name="turn_on", item_id="item_1")
            yield FunctionCallArgumentsDone(
                arguments='{"entity_id":"light.kitchen"}', item_id="item_1"
            )

    deltas = []
    async for delta in _events_to_deltas(FakeClient(), request):
        deltas.append(delta)

    assert deltas[0] == {"role": "assistant"}
    assert deltas[1] == {"content": "Hello"}
    assert deltas[2]["tool_calls"][0].tool_name == "turn_on"
    assert deltas[2]["tool_calls"][0].tool_args == {"entity_id": "light.kitchen"}


@pytest.mark.asyncio
async def test_async_run_chat_log_appends_final_assistant_content():
    chat_log = make_chat_log([UserContent(content="Hello")])

    class FakeClient:
        async def stream(self, request):
            yield OutputTextDelta(delta="Result text", content_index=0)

    await async_run_chat_log(
        chat_log=chat_log,
        client=FakeClient(),
        model="opencode-go/kimi-k3",
        entity_id="conversation.opencode_go_conversation",
        reasoning_effort="medium",
        reasoning_summary="off",
        text_verbosity="medium",
    )

    assert isinstance(chat_log.content[-1], AssistantContent)
    assert chat_log.content[-1].content == "Result text"


def test_json_default_date_and_datetime():
    assert json_default(date(2026, 3, 3)) == "2026-03-03"
    assert json_default(datetime(2026, 3, 3, 15, 0, 0)) == "2026-03-03T15:00:00"
