"""Tests for the OpenCode Go config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.opencode_go_conversation.config_flow import (
    OpenCodeGoConversationConfigFlow,
    _async_fetch_models,
)
from custom_components.opencode_go_conversation.const import MODELS
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

    assert result["type"] == "create_entry"
    assert result["title"] == "OpenCode Go"
    assert result["data"]["api_key"] == "test_api_key"
    assert len(result["subentries"]) == 2


@pytest.mark.asyncio
async def test_user_step_shows_error_on_invalid_api_key(hass):
    flow = OpenCodeGoConversationConfigFlow()
    flow.hass = hass

    with patch(
        "custom_components.opencode_go_conversation.config_flow._async_validate_api_key",
        new=AsyncMock(side_effect=OpenCodeGoApiError(401, "nope")),
    ):
        result = await flow.async_step_user({"api_key": "bad"})

    assert result["type"] == "form"
    assert result["errors"]["base"] == "invalid_auth"


@pytest.mark.asyncio
async def test_fetch_models_falls_back_to_snapshot_on_failure(hass):
    with (
        patch(
            "custom_components.opencode_go_conversation.config_flow.OpenCodeGoClient.list_models",
            new=AsyncMock(side_effect=Exception("boom")),
        ),
        patch(
            "custom_components.opencode_go_conversation.config_flow.async_get_clientsession"
        ),
    ):
        models = await _async_fetch_models(hass, "test_api_key")

    assert models == MODELS
