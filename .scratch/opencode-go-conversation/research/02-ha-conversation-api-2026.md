# Research: Home Assistant conversation API (2026.x)

## Summary

Home Assistant’s current conversation entity API is still based on `homeassistant.components.conversation.ConversationEntity`, with message handling in `_async_handle_message(user_input, chat_log)` and streaming/tool support driven by `ChatLog`.

## Findings

### Entity shape

- The official docs still derive conversation entities from `ConversationEntity`.
- `supported_languages` is a required property.
- `ConversationEntityFeature.CONTROL` is the feature flag for entities that control HA.

### Message handling

- The current handler is `_async_handle_message(self, user_input: ConversationInput, chat_log: ChatLog) -> ConversationResult`.
- The docs note the old `async_process` name was changed to `_async_handle_message`.
- The recommended non-streaming helper is `chat_log.async_add_assistant_content_without_tools(...)`.

### ChatLog / streaming

- `ChatLog` is the typed API for history, tool calls, and streamed assistant content.
- In core (`homeassistant/components/conversation/chat_log.py`), the streaming helper is `async_add_delta_content_stream(...)`, which consumes deltas with `role`, `content`, `thinking_content`, `tool_calls`, and `tool_result`.
- The chat log can also execute tool calls with `async_add_assistant_content(...)`.

### Config flow / subentries

- The official config-flow docs include `ConfigSubentryFlow` and `async_get_supported_subentry_types(...)`.
- Subentries are still created through a main config entry, and the docs explicitly describe subentry reconfigure support.
- `ConfigFlow.async_create_entry(...)` in core accepts a `subentries=` parameter.

## Implications for this integration

- We can keep the source’s structure: main config entry for auth, subentries for conversation / ai_task settings.
- Streaming should be implemented using `ChatLog.async_add_delta_content_stream(...)` / `async_add_assistant_content_without_tools(...)` in the current core API.
- Tool calls are still part of the conversation log and should be wired through if the backend supports them.

## Sources

- https://developers.home-assistant.io/docs/core/entity/conversation
- https://developers.home-assistant.io/docs/core/integration/config_flow
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/conversation/chat_log.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/config_entries.py
