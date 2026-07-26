Type: research
Status: resolved

## Question

¿Cuál es la forma actual (HA 2026.x) de implementar un `ai_task.AITaskEntity` y de exponer la generación de datos estructurados como subentry?

La fuente `hass-codex-conversation` implementa `ai_task` con `generate_data` (estructurado) y referencia `generate_image` (no implementado). Queremos confirmar antes de replicar:

- **`ai_task.AITaskEntity`**: signature actual de `async def _async_generate_data(self, task, chat_log, attachments)`. ¿Cómo se accede al `task.structure` (el schema que pide el llamante)? ¿Cómo se devuelve el `GenDataResult` con `data` y opcionalmente `conversation_id`?
- **`generate_content`**: la API moderna de HA 2026.x añadió `generate_content` para texto plano con opcional JSON schema. ¿Lo cubrimos? ¿O solo `generate_data` para mantener paridad con la fuente?
- **`generate_image`**: ¿lo implementamos o no? Los modelos de Go son todos de código/texto (Grok 4.5, GLM-5.2, Kimi K3, etc.), no generativos de imagen. Recomendación: **no implementarlo** y abortar con `NotSupportedError` si alguien lo pide. A confirmar en este ticket.
- **Subentry flow** para `ai_task`: igual patrón que para `conversation`, con un subentry de tipo `ai_task_data` que expone modelo + reasoning controls.
- **Errores**: `AITaskEntity` levanta `HomeAssistantError` para fallos; ¿hay una jerarquía más fina (`AITaskNoSupportError`, `AITaskRateLimitError`)? ¿Cómo se reporta al usuario?
- **Integración con `conversation.ChatLog`**: el agente de conversación puede delegar a `ai_task`. ¿Cómo se enlazan en HA 2026.x?

## Resolution path

Capturar los hallazgos en una branch `research/ha-ai-task-api-2026` con un puntero desde este ticket. Fuentes esperadas:

1. `developers.home-assistant.io/docs/core/entity/ai_task` — referencia canónica.
2. El código de `home-assistant/core` para `AITaskEntity` en la rama `2026.x`.
3. La fuente `hass-codex-conversation` como baseline.

Cuando cierre, este ticket desbloquea la escritura de `ai_task.py` en este repo y la decisión (grilling) sobre `generate_image`.

## Skills to consult

- Documentación de desarrollo de Home Assistant (`developers.home-assistant.io`).

## Answer

The current AI Task API in Home Assistant centers on `AITaskEntity` with two overridable methods:

- `_async_generate_data(self, task: GenDataTask, chat_log: ChatLog) -> GenDataTaskResult`
- `_async_generate_image(self, task: GenImageTask, chat_log: ChatLog) -> GenImageTaskResult`

`GenDataTask` carries `name`, `instructions`, optional `structure`, optional `attachments`, and optional `llm_api`. Core builds a `ChatLog`, wires LLM context, and adds the user instructions before calling the entity.

For this integration, the important conclusion is that the source `hass-codex-conversation` only implements the data path; there is no image generation implementation to mirror. So the first release should expose `generate_data` only and leave `generate_image` unsupported.

Implication for the integration: keep AI Task limited to structured data generation, feed the prompt through the `ChatLog`, and return `GenDataTaskResult(conversation_id, data)`.

## Comments

