"""Tests for the AI Task entity."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

from homeassistant.components import ai_task as ai_task_component
from homeassistant.components.conversation import AssistantContent
from homeassistant.config_entries import ConfigSubentry
import pytest
import voluptuous as vol

from custom_components.opencode_go_conversation.ai_task import (
    OpenCodeGoAITaskEntity,
    _format_structure_instruction,
)
from custom_components.opencode_go_conversation.opencode_api import OutputTextDelta

from .conftest import make_chat_log


@pytest.fixture
def mock_ai_task_entity(hass, mock_config_entry, mock_ai_task_subentry):
    entity = OpenCodeGoAITaskEntity(
        hass,
        mock_config_entry,
        "test_api_key",
        cast(ConfigSubentry, mock_ai_task_subentry),
    )
    entity.entity_id = "ai_task.opencode_go_conversation"
    entity.hass = hass
    return entity


async def test_generate_data_returns_text_result(mock_ai_task_entity):
    chat_log = make_chat_log(
        [
            AssistantContent(
                agent_id="ai_task.agent", content="Result text", tool_calls=None
            )
        ]
    )
    chat_log.conversation_id = "conv-1"
    task = MagicMock(spec=ai_task_component.GenDataTask)
    task.structure = None
    task.name = "summarize"

    class FakeClient:
        async def stream(self, request):
            yield OutputTextDelta(delta="Result text", content_index=0)

    with patch(
        "custom_components.opencode_go_conversation.ai_task.OpenCodeGoClient",
        return_value=FakeClient(),
    ):
        result = await mock_ai_task_entity._async_generate_data(task, chat_log)

    assert result.conversation_id == "conv-1"
    assert result.data == "Result text"


async def test_generate_data_parses_json_result(mock_ai_task_entity):
    chat_log = make_chat_log(
        [
            AssistantContent(
                agent_id="ai_task.agent", content='{"answer":"ok"}', tool_calls=None
            )
        ]
    )
    chat_log.conversation_id = "conv-2"
    task = MagicMock(spec=ai_task_component.GenDataTask)
    task.structure = vol.Schema({vol.Required("answer"): str})
    task.name = "extract"

    class FakeClient:
        async def stream(self, request):
            yield OutputTextDelta(delta='{"answer":"ok"}', content_index=0)

    with patch(
        "custom_components.opencode_go_conversation.ai_task.OpenCodeGoClient",
        return_value=FakeClient(),
    ):
        result = await mock_ai_task_entity._async_generate_data(task, chat_log)

    assert result.conversation_id == "conv-2"
    assert result.data == {"answer": "ok"}


async def test_ai_task_entity_supports_attachments(mock_ai_task_entity):
    assert (
        mock_ai_task_entity.supported_features
        & ai_task_component.AITaskEntityFeature.SUPPORT_ATTACHMENTS
    )


def test_format_structure_instruction():
    task = MagicMock(spec=ai_task_component.GenDataTask)
    task.structure = vol.Schema({vol.Required("name"): str, vol.Optional("age"): int})

    instruction = _format_structure_instruction(task)

    assert "Return only valid JSON." in instruction
    assert "name" in instruction
    assert "age" in instruction
