Type: research
Status: resolved

## Question

¿Cuál es la forma actual (HA 2026.x) de implementar un `conversation.ConversationEntity` y de exponer un config-flow con subentries para los ajustes de conversación (modelo, prompt, LLM HASS API, reasoning controls)?

La fuente `hass-codex-conversation` se escribió contra una versión snapshot de la API de HA. Antes de replicarla, queremos confirmar:

- **`conversation.ConversationEntity`**: signature actual de `async def _async_handle_message(self, user_input, chat_log)`. ¿Sigue siendo `_async_handle_message` o ha pasado a otro nombre? ¿Cuál es la nueva forma de `chat_log.async_add_assistant_content(...)`? ¿Cómo se hace streaming hoy (`AssistantContentDelta`, `agent_id` arguments, `async_add_delta_content` en el chat log, etc.)?
- **`ChatLog`**: API actual. ¿Cómo se itera el historial? ¿Cómo se accede a `llm_api`? ¿Cómo se inyectan los tools?
- **`llm` API de Home Assistant**: cómo se hace la consulta al Assist pipeline, qué IDs de API existen (`assist`, `no_entities`, etc.), cómo se mapean a `CONF_LLM_HASS_API` en el config flow.
- **Subentry flow**: ¿sigue siendo `ConfigSubentryFlow` el patrón canónico? ¿Hay un nuevo helper en 2026.x? ¿Cómo se declara `async_get_supported_subentry_types`?
- **Streaming de la respuesta**: cómo se marca el "primer token" para que la UI muestre la respuesta progresivamente, y cómo se cierra el stream.
- **Errores del agente**: `ConverseError` actual, qué atributos lleva, y cómo se traducen a `HomeAssistantError` que HA muestre al usuario.

## Resolution path

Capturar los hallazgos en una branch `research/ha-conversation-api-2026` con un puntero desde este ticket. Fuentes esperadas:

1. `developers.home-assistant.io/docs/config_entries_config_flow_handler` y subentry docs.
2. `developers.home-assistant.io/docs/core/entity/conversation` — la referencia canónica de la plataforma `conversation`.
3. El código de `home-assistant/core` para `ConversationEntity` y `ChatLog` en la rama `2026.x` (referenciar tag/branch concreto).
4. La fuente `hass-codex-conversation` como baseline de qué API usaba cuando se escribió, para identificar drift.

Cuando cierre, este ticket desbloquea la escritura de `conversation.py` en este repo.

## Skills to consult

- Documentación de desarrollo de Home Assistant (`developers.home-assistant.io`).

## Answer

The current Home Assistant conversation API still centers on `ConversationEntity` with `_async_handle_message(user_input, chat_log)`.

Key points:

- `supported_languages` is still required.
- `ConversationEntityFeature.CONTROL` is the feature flag for a controlling agent.
- The current handler is `_async_handle_message(self, user_input: ConversationInput, chat_log: ChatLog) -> ConversationResult`.
- For non-streaming assistant output, use `chat_log.async_add_assistant_content_without_tools(...)`.
- For streamed assistant output, core now exposes `chat_log.async_add_delta_content_stream(...)` and the lower-level `async_add_assistant_content(...)` / tool-result plumbing.
- Subentry flows are first-class (`ConfigSubentryFlow`, `async_get_supported_subentry_types`, `reconfigure` support), and `ConfigFlow.async_create_entry(..., subentries=[...])` is still supported in core.

Implication for the integration: we can keep the modern subentry-based layout from `hass-codex-conversation`, and implement streaming/tool calls against the current `ChatLog` API without inventing a custom transport.

## Comments

