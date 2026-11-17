"""OpenCode Go Conversation integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_KEY, DOMAIN
from .opencode_api import OpenCodeGoAuth, OpenCodeGoClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.AI_TASK, Platform.CONVERSATION]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the OpenCode Go integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenCode Go from a config entry."""
    api_key = entry.data[CONF_API_KEY]
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api_key": api_key,
    }

    # Warm the model catalog so the first conversation does not have to fetch
    # it.  A failure here is not fatal: the client retries on the next request.
    client = OpenCodeGoClient(OpenCodeGoAuth(async_get_clientsession(hass), api_key))
    try:
        await client.refresh_catalog()
    except Exception:
        _LOGGER.warning(
            "Could not refresh the OpenCode Go model catalog during setup",
            exc_info=True,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return True
    return False


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
