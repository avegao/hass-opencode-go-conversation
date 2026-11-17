"""Tests for the OpenCode Go config flow."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigEntryState
import pytest
import voluptuous as vol

from custom_components.opencode_go_conversation.config_flow import (
    OpenCodeGoConversationConfigFlow,
    OpenCodeGoConversationSubentryFlow,
    _async_fetch_models,
)
from custom_components.opencode_go_conversation.const import (
    CONF_MODEL,
    RECOMMENDED_AI_TASK_OPTIONS,
    RECOMMENDED_CONVERSATION_OPTIONS,
)
from custom_components.opencode_go_conversation.opencode_api import OpenCodeGoApiError


@pytest.mark.asyncio
async def test_user_step_creates_entry_on_valid_api_key(hass):
    flow = OpenCodeGoConversationConfigFlow()
    flow.hass = hass

    with patch(
        "custom_components.opencode_go_conversation.config_flow._async_validate_api_key",
        new=AsyncMock(),
    ):
        result = await flow.async_step_user({"api_key": "test_api_key"})

    subentries = list(result["subentries"])

    assert result["type"] == "create_entry"
    assert result["title"] == "OpenCode Go"
    assert result["data"]["api_key"] == "test_api_key"
    assert len(subentries) == 2


@pytest.mark.asyncio
async def test_user_step_shows_error_on_invalid_api_key(hass):
    flow = OpenCodeGoConversationConfigFlow()
    flow.hass = hass

    with patch(
        "custom_components.opencode_go_conversation.config_flow._async_validate_api_key",
        new=AsyncMock(side_effect=OpenCodeGoApiError(401, "nope")),
    ):
        result = await flow.async_step_user({"api_key": "bad"})

    errors = result["errors"]

    assert result["type"] == "form"
    assert errors is not None
    assert errors["base"] == "invalid_auth"


@pytest.mark.asyncio
async def test_reconfigure_step_updates_api_key(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)

    flow = OpenCodeGoConversationConfigFlow()
    flow.hass = hass
    flow.context = {
        "source": SOURCE_RECONFIGURE,
        "entry_id": mock_config_entry.entry_id,
    }

    with patch(
        "custom_components.opencode_go_conversation.config_flow._async_validate_api_key",
        new=AsyncMock(),
    ):
        result = await flow.async_step_reconfigure({"api_key": "new_api_key"})

    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data["api_key"] == "new_api_key"


@pytest.mark.asyncio
async def test_fetch_models_uses_the_live_catalog(hass):
    with (
        patch(
            "custom_components.opencode_go_conversation.config_flow.OpenCodeGoClient.list_models",
            new=AsyncMock(return_value=["opencode-go/deepseek-v4.1-flash"]),
        ),
        patch(
            "custom_components.opencode_go_conversation.config_flow.async_get_clientsession"
        ),
    ):
        models = await _async_fetch_models(hass, "test_api_key")

    assert models == ["opencode-go/deepseek-v4.1-flash"]


@pytest.mark.asyncio
async def test_fetch_models_does_not_fall_back_to_a_stale_snapshot(hass):
    with (
        patch(
            "custom_components.opencode_go_conversation.config_flow.OpenCodeGoClient.list_models",
            new=AsyncMock(side_effect=Exception("boom")),
        ),
        patch(
            "custom_components.opencode_go_conversation.config_flow.async_get_clientsession"
        ),
        pytest.raises(Exception, match="boom"),
    ):
        await _async_fetch_models(hass, "test_api_key")


@pytest.mark.asyncio
async def test_init_step_requires_a_model_without_preselecting_one(hass):
    flow = OpenCodeGoConversationSubentryFlow()
    flow.hass = hass
    flow.options = {}
    flow._init_data = {}

    with (
        patch.object(
            flow,
            "_get_entry",
            return_value=SimpleNamespace(state=ConfigEntryState.LOADED),
        ),
        patch.object(
            flow,
            "_async_model_options",
            new=AsyncMock(return_value=["opencode-go/deepseek-v4.1-flash"]),
        ),
    ):
        result = await flow.async_step_init()

    data_schema = result["data_schema"]
    assert data_schema is not None
    model_key = next(key for key in data_schema.schema if str(key) == "model")
    assert isinstance(model_key, vol.Marker)
    assert model_key.default is vol.UNDEFINED


def test_recommended_options_do_not_pin_a_model():
    assert CONF_MODEL not in RECOMMENDED_CONVERSATION_OPTIONS
    assert CONF_MODEL not in RECOMMENDED_AI_TASK_OPTIONS
