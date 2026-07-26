"""Config flow for OpenCode Go Conversation."""

from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import callback
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TemplateSelector,
)
import voluptuous as vol

from .const import (
    CONF_API_KEY,
    CONF_MODEL,
    CONF_PROMPT,
    CONF_REASONING_EFFORT,
    CONF_REASONING_SUMMARY,
    CONF_RECOMMENDED,
    CONF_TEXT_VERBOSITY,
    DEFAULT_MODEL,
    DOMAIN,
    MODELS,
    RECOMMENDED_AI_TASK_OPTIONS,
    RECOMMENDED_CONVERSATION_OPTIONS,
    RECOMMENDED_REASONING_EFFORT,
    RECOMMENDED_REASONING_SUMMARY,
    RECOMMENDED_TEXT_VERBOSITY,
)
from .opencode_api import (
    OpenCodeGoApiError,
    OpenCodeGoAuth,
    OpenCodeGoClient,
    OpenCodeGoRateLimited,
    OpenCodeGoServerOverloaded,
)

_LOGGER = logging.getLogger(__name__)


async def _async_validate_api_key(hass, api_key: str) -> None:
    """Ensure the provided API key can list models."""
    session = async_get_clientsession(hass)
    client = OpenCodeGoClient(OpenCodeGoAuth(session, api_key))
    await client.list_models()


async def _async_fetch_models(hass, api_key: str) -> list[str]:
    """Fetch model ids from OpenCode Go, falling back to the docs snapshot."""
    session = async_get_clientsession(hass)
    client = OpenCodeGoClient(OpenCodeGoAuth(session, api_key))
    try:
        models = await client.list_models()
    except Exception:
        _LOGGER.exception("Failed to fetch models from OpenCode Go; using fallback")
        return MODELS
    return models or MODELS


class OpenCodeGoConversationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow: ask for API key, then configure subentries."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            try:
                await _async_validate_api_key(self.hass, api_key)
            except (
                OpenCodeGoApiError,
                OpenCodeGoRateLimited,
                OpenCodeGoServerOverloaded,
            ):
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Failed to validate OpenCode Go API key")
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="OpenCode Go",
                    data={CONF_API_KEY: api_key},
                    subentries=[
                        {
                            "subentry_type": "conversation",
                            "data": RECOMMENDED_CONVERSATION_OPTIONS,
                            "title": "OpenCode Go Conversation",
                            "unique_id": None,
                        },
                        {
                            "subentry_type": "ai_task_data",
                            "data": RECOMMENDED_AI_TASK_OPTIONS,
                            "title": "OpenCode Go AI Task",
                            "unique_id": None,
                        },
                    ],
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {
            "conversation": OpenCodeGoConversationSubentryFlow,
            "ai_task_data": OpenCodeGoAITaskSubentryFlow,
        }


class _BaseOpenCodeGoSubentryFlow(ConfigSubentryFlow):
    """Base flow for OpenCode Go subentries using model settings."""

    options: dict[str, Any]
    _init_data: dict[str, Any]

    @property
    def _is_new(self) -> bool:
        return self.source == "user"

    @property
    def _default_data(self) -> dict[str, Any]:
        raise NotImplementedError

    @property
    def _supports_prompt_and_apis(self) -> bool:
        return False

    async def _async_model_options(self) -> list[str]:
        api_key = self._get_entry().data[CONF_API_KEY]
        return await _async_fetch_models(self.hass, api_key)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        self.options = self._default_data.copy()
        self._init_data = {}
        return await self.async_step_init()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        self.options = self._get_reconfigure_subentry().data.copy()
        self._init_data = {}
        return await self.async_step_init()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if self._get_entry().state != ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")

        options = self.options
        if user_input is not None:
            if user_input[CONF_RECOMMENDED]:
                data = self._default_data.copy()
                if self._supports_prompt_and_apis:
                    data[CONF_PROMPT] = user_input.get(
                        CONF_PROMPT, llm.DEFAULT_INSTRUCTIONS_PROMPT
                    )
                    data[CONF_LLM_HASS_API] = user_input.get(CONF_LLM_HASS_API) or []
                return self._finalize_subentry(data)

            self._init_data = user_input
            return await self.async_step_advanced()

        if self._supports_prompt_and_apis:
            hass_apis: list[SelectOptionDict] = [
                {"value": api.id, "label": api.name}
                for api in llm.async_get_apis(self.hass)
            ]
            step_schema: dict = {
                vol.Optional(
                    CONF_PROMPT,
                    description={
                        "suggested_value": options.get(
                            CONF_PROMPT, llm.DEFAULT_INSTRUCTIONS_PROMPT
                        )
                    },
                ): TemplateSelector(),
                vol.Optional(CONF_LLM_HASS_API): SelectSelector(
                    SelectSelectorConfig(
                        options=cast(list[SelectOptionDict] | list[str], hass_apis),
                        multiple=True,
                    )
                ),
                vol.Required(
                    CONF_RECOMMENDED,
                    default=options.get(CONF_RECOMMENDED, True),
                ): bool,
            }
        else:
            step_schema = {
                vol.Required(
                    CONF_RECOMMENDED,
                    default=options.get(CONF_RECOMMENDED, True),
                ): bool,
            }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(step_schema))

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        options = self.options

        if user_input is not None:
            data = {**self._init_data, **user_input}
            return self._finalize_subentry(data)

        model_options = await self._async_model_options()
        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODEL,
                        default=options.get(CONF_MODEL, DEFAULT_MODEL),
                    ): SelectSelector(
                        SelectSelectorConfig(options=list(model_options))
                    ),
                    vol.Required(
                        CONF_REASONING_EFFORT,
                        default=options.get(
                            CONF_REASONING_EFFORT, RECOMMENDED_REASONING_EFFORT
                        ),
                    ): SelectSelector(
                        SelectSelectorConfig(options=["low", "medium", "high"])
                    ),
                    vol.Required(
                        CONF_REASONING_SUMMARY,
                        default=options.get(
                            CONF_REASONING_SUMMARY, RECOMMENDED_REASONING_SUMMARY
                        ),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=["auto", "short", "detailed", "off"]
                        )
                    ),
                    vol.Required(
                        CONF_TEXT_VERBOSITY,
                        default=options.get(
                            CONF_TEXT_VERBOSITY, RECOMMENDED_TEXT_VERBOSITY
                        ),
                    ): SelectSelector(
                        SelectSelectorConfig(options=["low", "medium", "high"])
                    ),
                }
            ),
        )

    def _finalize_subentry(self, data: dict[str, Any]) -> SubentryFlowResult:
        model = data.get(CONF_MODEL, DEFAULT_MODEL)
        title = f"OpenCode Go ({model.removeprefix('opencode-go/')})"

        if self._is_new:
            return self.async_create_entry(title=title, data=data)

        return self.async_update_and_abort(
            self._get_entry(),
            self._get_reconfigure_subentry(),
            data=data,
            title=title,
        )


class OpenCodeGoConversationSubentryFlow(_BaseOpenCodeGoSubentryFlow):
    """Flow for OpenCode Go conversation subentries."""

    @property
    def _default_data(self) -> dict[str, Any]:
        return RECOMMENDED_CONVERSATION_OPTIONS

    @property
    def _supports_prompt_and_apis(self) -> bool:
        return True


class OpenCodeGoAITaskSubentryFlow(_BaseOpenCodeGoSubentryFlow):
    """Flow for OpenCode Go AI task subentries."""

    @property
    def _default_data(self) -> dict[str, Any]:
        return RECOMMENDED_AI_TASK_OPTIONS
