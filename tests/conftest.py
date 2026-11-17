"""Shared fixtures for the OpenCode Go Conversation tests."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

_turbojpeg_module = ModuleType("turbojpeg")
setattr(_turbojpeg_module, "TurboJPEG", type("_TurboJPEG", (), {}))
sys.modules.setdefault("turbojpeg", _turbojpeg_module)

from homeassistant.config_entries import ConfigSubentry  # noqa: E402
import pytest  # noqa: E402
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.opencode_go_conversation.ai_task import (  # noqa: E402
    OpenCodeGoAITaskEntity,
)
from custom_components.opencode_go_conversation.const import (  # noqa: E402
    CONF_API_KEY,
    CONF_MODEL,
    DOMAIN,
    RECOMMENDED_AI_TASK_OPTIONS,
    RECOMMENDED_CONVERSATION_OPTIONS,
)
from custom_components.opencode_go_conversation.conversation import (  # noqa: E402
    OpenCodeGoConversationEntity,
)
from custom_components.opencode_go_conversation.opencode_api.routing import (  # noqa: E402
    MODEL_CATALOG,
    ModelRoute,
)

ENTRY_ID = "test_entry_id"
TEST_MODEL = "opencode-go/deepseek-v4.1-flash"


@pytest.fixture(autouse=True)
def model_catalog():
    """Seed the shared catalog so tests never hit the network by accident."""
    MODEL_CATALOG.replace(
        {
            "deepseek-v4.1-flash": ModelRoute(
                "deepseek-v4.1-flash", "chat", "/chat/completions"
            ),
            "gpt-5.6-luna": ModelRoute("gpt-5.6-luna", "responses", "/responses"),
            "qwen3.8-max": ModelRoute("qwen3.8-max", "anthropic", "/messages"),
            "kimi-k3": ModelRoute("kimi-k3", "chat", "/chat/completions"),
        }
    )
    yield
    MODEL_CATALOG.reset()


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=ENTRY_ID,
        data={CONF_API_KEY: "test_api_key"},
        options=RECOMMENDED_CONVERSATION_OPTIONS,
    )


@pytest.fixture
def mock_entity(hass, mock_config_entry) -> OpenCodeGoConversationEntity:
    conversation_subentry = SimpleNamespace(
        subentry_id="conversation_subentry_id",
        title="OpenCode Go Conversation",
        data={CONF_MODEL: TEST_MODEL, **RECOMMENDED_CONVERSATION_OPTIONS},
        subentry_type="conversation",
    )
    entity = OpenCodeGoConversationEntity(
        hass,
        mock_config_entry,
        "test_api_key",
        cast(ConfigSubentry, conversation_subentry),
    )
    entity.entity_id = f"conversation.{DOMAIN}"
    entity.hass = hass
    return entity


@pytest.fixture
def mock_ai_task_subentry() -> SimpleNamespace:
    return SimpleNamespace(
        subentry_id="ai_task_subentry_id",
        title="OpenCode Go AI Task",
        data={CONF_MODEL: TEST_MODEL, **RECOMMENDED_AI_TASK_OPTIONS},
        subentry_type="ai_task_data",
    )


@pytest.fixture
def mock_ai_task_entity(
    hass, mock_config_entry, mock_ai_task_subentry: SimpleNamespace
):
    entity = OpenCodeGoAITaskEntity(
        hass,
        mock_config_entry,
        "test_api_key",
        cast(ConfigSubentry, mock_ai_task_subentry),
    )
    entity.entity_id = f"ai_task.{DOMAIN}"
    entity.hass = hass
    return entity


async def drain_generator(entity_id, gen):
    content_chunks: list[str] = []
    async for delta in gen:
        if isinstance(delta, dict) and delta.get("content"):
            content_chunks.append(delta["content"])
    if content_chunks:
        from homeassistant.components.conversation import AssistantContent

        chat_log = getattr(drain_generator, "_chat_log", None)
        if chat_log is not None:
            chat_log.content.append(
                AssistantContent(
                    agent_id=entity_id,
                    content="".join(content_chunks),
                    tool_calls=None,
                )
            )
    if False:
        yield None


def make_chat_log(content: list, *, llm_api=None, unresponded=False) -> MagicMock:
    chat_log = MagicMock()
    chat_log.async_provide_llm_data = AsyncMock()
    chat_log.async_add_delta_content_stream = drain_generator
    setattr(drain_generator, "_chat_log", chat_log)
    chat_log.content = content
    chat_log.llm_api = llm_api
    chat_log.unresponded_tool_results = unresponded
    chat_log.hass = SimpleNamespace(
        async_add_executor_job=AsyncMock(
            side_effect=lambda target, *args: target(*args)
        )
    )
    chat_log.conversation_id = "conv-test"
    return chat_log
