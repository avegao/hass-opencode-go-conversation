"""Tests for integration setup / teardown (__init__.py)."""

from __future__ import annotations

from unittest.mock import patch

from custom_components.opencode_go_conversation import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.opencode_go_conversation.const import DOMAIN


async def test_async_setup_returns_true(hass):
    assert await async_setup(hass, {}) is True


async def test_async_setup_entry_stores_api_key(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)

    with patch.object(
        hass.config_entries, "async_forward_entry_setups", return_value=True
    ):
        result = await async_setup_entry(hass, mock_config_entry)

    assert result is True
    assert hass.data[DOMAIN][mock_config_entry.entry_id]["api_key"] == "test_api_key"


async def test_async_unload_entry_removes_data(hass, mock_config_entry):
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = {
        "api_key": "test_api_key"
    }

    with patch.object(hass.config_entries, "async_unload_platforms", return_value=True):
        result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})
