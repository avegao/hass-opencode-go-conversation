"""Conversation platform — OpenCode Go agent."""

from __future__ import annotations

from collections.abc import AsyncGenerator
import json
import logging
from typing import Any, Literal

from homeassistant.components import conversation
from homeassistant.components.conversation import (
    AssistantContentDeltaDict,
    ChatLog,
    ConversationEntity,
    ConversationInput,
    ConversationResult,
    ConverseError,
    UserContent,
)
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_LLM_HASS_API, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, intent, llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_MODEL,
    CONF_PROMPT,
    CONF_REASONING_EFFORT,
    CONF_REASONING_SUMMARY,
    CONF_TEXT_VERBOSITY,
    DEFAULT_MODEL,
    DOMAIN,
    RECOMMENDED_REASONING_EFFORT,
    RECOMMENDED_REASONING_SUMMARY,
    RECOMMENDED_TEXT_VERBOSITY,
)
from .opencode_api import (
    FunctionCallAdded,
    FunctionCallArgumentsDone,
    OpenCodeGoApiError,
    OpenCodeGoAuth,
    OpenCodeGoClient,
    OpenCodeGoContextWindowExceeded,
    OpenCodeGoError,
    OpenCodeGoQuotaExceeded,
    OpenCodeGoRateLimited,
    OpenCodeGoRequest,
    OpenCodeGoServerOverloaded,
    OutputItemDone,
    OutputTextDelta,
    ReasoningSummaryDelta,
)
from .transform import (
    async_prepare_files_for_prompt,
    build_chat_messages,
    build_input_items,
    extract_instructions,
    format_tool,
)

_LOGGER = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10
NO_EXPOSED_ENTITIES_SUFFIX = (
    "If the user asks a general knowledge question or makes casual conversation, "
    "answer normally in plain text and do not mention missing tools, entities, or "
    "integration limitations. Only mention exposing entities in Home Assistant when "
    "the user is explicitly trying to control or inspect their home devices."
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    api_key = hass.data[DOMAIN][entry.entry_id]["api_key"]

    for subentry in entry.subentries.values():
        if subentry.subentry_type != "conversation":
            continue
        async_add_entities(
            [OpenCodeGoConversationEntity(hass, entry, api_key, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class OpenCodeGoConversationEntity(
    ConversationEntity, conversation.AbstractConversationAgent
):
    """Conversation agent backed by OpenCode Go."""

    _attr_has_entity_name = True
    _attr_name = "Assist"
    _attr_supports_streaming = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api_key: str,
        subentry: ConfigSubentry,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._subentry = subentry
        self._api_key = api_key
        self._attr_unique_id = subentry.subentry_id
        self._attr_name = subentry.title
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=subentry.title,
            manufacturer="OpenCode",
            model=self._options.get(CONF_MODEL, DEFAULT_MODEL),
            entry_type=dr.DeviceEntryType.SERVICE,
        )

        if self._options.get(CONF_LLM_HASS_API):
            self._attr_supported_features = (
                conversation.ConversationEntityFeature.CONTROL
            )

    @property
    def _options(self) -> Any:
        return self._subentry.data

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self._entry, self)

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self._entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: ConversationInput,
        chat_log: ChatLog,
    ) -> ConversationResult:
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                self._options.get(CONF_LLM_HASS_API),
                self._options.get(CONF_PROMPT),
                user_input.extra_system_prompt,
            )
        except ConverseError as err:
            return err.as_conversation_result()

        client = OpenCodeGoClient(
            OpenCodeGoAuth(async_get_clientsession(self.hass), self._api_key)
        )
        await async_run_chat_log(
            chat_log=chat_log,
            client=client,
            model=self._options.get(CONF_MODEL, DEFAULT_MODEL),
            entity_id=self.entity_id,
            reasoning_effort=self._options.get(
                CONF_REASONING_EFFORT, RECOMMENDED_REASONING_EFFORT
            ),
            reasoning_summary=self._options.get(
                CONF_REASONING_SUMMARY, RECOMMENDED_REASONING_SUMMARY
            ),
            text_verbosity=self._options.get(
                CONF_TEXT_VERBOSITY, RECOMMENDED_TEXT_VERBOSITY
            ),
            error_cls=ConverseError,
        )

        return conversation.async_get_result_from_chat_log(user_input, chat_log)


async def async_run_chat_log(
    *,
    chat_log: ChatLog,
    client: OpenCodeGoClient,
    model: str,
    entity_id: str,
    reasoning_effort: str,
    reasoning_summary: str,
    text_verbosity: str,
    max_iterations: int = MAX_TOOL_ITERATIONS,
    instructions_suffix: str = "",
    error_cls: type[Exception] = HomeAssistantError,
) -> None:
    """Execute a ChatLog against the model's OpenCode Go API protocol."""
    llm_api = chat_log.llm_api
    custom_serializer = (
        getattr(llm_api, "custom_serializer", None) if llm_api is not None else None
    )
    tools = (
        [
            format_tool(tool, custom_serializer=custom_serializer)
            for tool in llm_api.tools
        ]
        if llm_api is not None
        else []
    )
    instructions = extract_instructions(chat_log)
    no_entities_prompt = getattr(llm, "NO_ENTITIES_PROMPT", None)
    if (
        llm_api is not None
        and no_entities_prompt is not None
        and llm_api.api_prompt == no_entities_prompt
    ):
        instructions = (
            f"{instructions}\n\n{NO_EXPOSED_ENTITIES_SUFFIX}"
            if instructions
            else NO_EXPOSED_ENTITIES_SUFFIX
        )
    if instructions_suffix:
        instructions = (
            f"{instructions}\n\n{instructions_suffix}"
            if instructions
            else instructions_suffix
        )

    # OpenCode Go uses this value for prompt-cache affinity.  Home Assistant
    # keeps ``conversation_id`` stable for the lifetime of a conversation.  Do
    # not send a made-up per-request value if a custom ChatLog violates that
    # contract: a missing stable ID would defeat the provider's cache routing.
    conversation_id = getattr(chat_log, "conversation_id", None)
    if not isinstance(conversation_id, str) or not conversation_id.strip():
        raise HomeAssistantError(
            "OpenCode Go requires a stable Home Assistant conversation ID"
        )
    session_id = conversation_id.strip()

    # Keep every caller (including future platforms) within the same bounded
    # provider-turn budget.  This prevents an accidental tool loop from
    # generating an unbounded burst of OpenCode Go traffic.
    for _iteration in range(min(max_iterations, MAX_TOOL_ITERATIONS)):
        messages = build_chat_messages(chat_log, system_prompt=instructions)
        input_items = build_input_items(chat_log)
        last_content = chat_log.content[-1]
        if isinstance(last_content, UserContent) and last_content.attachments:
            files = await async_prepare_files_for_prompt(
                chat_log.hass,
                [(a.path, a.mime_type) for a in last_content.attachments],
            )
            for message in reversed(messages):
                if message.get("role") != "user":
                    continue
                content = message.get("content")
                if isinstance(content, str):
                    message["content"] = [{"type": "text", "text": content}, *files]
                elif isinstance(content, list):
                    content.extend(files)
                break
            for item in reversed(input_items):
                if item.get("type") != "message" or item.get("role") != "user":
                    continue
                content = item.get("content")
                if isinstance(content, list):
                    content.extend(files)
                break

        request = OpenCodeGoRequest(
            model=model,
            messages=messages,
            tools=tools,
            reasoning_effort=reasoning_effort,
            session_id=session_id,
            input_items=input_items,
            instructions=instructions,
        )

        try:
            async for _ in chat_log.async_add_delta_content_stream(
                entity_id,
                _events_to_deltas(client, request),
            ):
                pass
        except (
            OpenCodeGoApiError,
            OpenCodeGoContextWindowExceeded,
            OpenCodeGoQuotaExceeded,
            OpenCodeGoRateLimited,
            OpenCodeGoServerOverloaded,
            OpenCodeGoError,
        ) as err:
            _LOGGER.error("OpenCodeGo error: %s", err)
            if error_cls is ConverseError:
                raise ConverseError(
                    str(err),
                    chat_log.conversation_id or "",
                    intent.IntentResponse(language="en"),
                ) from err
            raise error_cls(str(err)) from err

        if not chat_log.unresponded_tool_results:
            break


async def _events_to_deltas(
    client: OpenCodeGoClient,
    request: OpenCodeGoRequest,
) -> AsyncGenerator[AssistantContentDeltaDict, None]:
    """Convert OpenCode Go ResponseEvents to HA delta dictionaries."""
    started = False
    pending_calls: dict[str, tuple[str, str]] = {}

    async for event in client.stream(request):
        if isinstance(event, OutputTextDelta) and event.delta:
            if not started:
                yield {"role": "assistant"}
                started = True
            yield {"content": event.delta}

        elif isinstance(event, FunctionCallAdded):
            pending_calls[event.item_id] = (event.call_id, event.name)
            if not started:
                yield {"role": "assistant"}
                started = True

        elif isinstance(event, FunctionCallArgumentsDone):
            call_id, name = pending_calls.get(event.item_id, ("", ""))
            try:
                tool_args = json.loads(event.arguments or "{}")
            except json.JSONDecodeError:
                tool_args = {}
            yield {
                "tool_calls": [
                    llm.ToolInput(
                        id=call_id,
                        tool_name=name,
                        tool_args=tool_args,
                    )
                ]
            }

        elif isinstance(event, OutputItemDone):
            if event.item.get("type") == "reasoning":
                if not started:
                    yield {"role": "assistant"}
                    started = True
                yield {"native": event.item}

        elif isinstance(event, ReasoningSummaryDelta):
            _LOGGER.debug("OpenCodeGo reasoning summary: %.80s", event.delta)
