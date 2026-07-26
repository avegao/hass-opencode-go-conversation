Type: grilling
Status: resolved
Blocked by: 01

## Question

¿El backend de OpenCode Go soporta streaming de respuestas? Si sí, ¿en qué formato? Y, en función de eso, ¿qué patrón de implementación usamos en `conversation.py` y `ai_task.py`?

El contexto: la fuente `hass-codex-conversation` hace streaming SSE con el backend de OpenCodeGo, y HA 2026.x lo soporta de forma nativa vía `chat_log.async_add_delta_content(...)` y `AssistantContentDelta`. Si Go **no** soporta streaming, perdemos la UX de "el texto aparece progresivamente" que es una de las features de paridad 1:1 que el usuario pidió.

Preguntas a resolver cuando el ticket 01 cierre:

- ¿Go devuelve un único JSON al final, o streamea tokens?
- Si streamea, ¿es SSE estilo OpenAI (`data: {"choices":[{"delta":...}]}\n\n` + `data: [DONE]`), o es otro formato (NDJSON, chunked HTTP, WebSocket, …)?
- ¿Los modelos que más nos importan (Grok 4.5, GLM-5.2, Kimi K3) streamean, o solo algunos?

Tres caminos según lo que encontremos:

- **(a) Streaming SSE estilo OpenAI, todos los modelos.** Caso ideal: reusamos un parser SSE genérico (la fuente ya tiene `opencode_api/sse.py`; lo adaptamos) y la UX de streaming se mantiene. **Recomendado** si la investigación lo confirma.
- **(b) Sin streaming, JSON único.** Más simple. La integración devuelve la respuesta completa de una. UX inferior (latencia percibida mayor), pero funcional. La paridad 1:1 con la fuente se rompe en este punto, y el subentry "advanced" ya no necesita un flag de "enable streaming".
- **(c) Streaming parcial — algunos modelos sí, otros no.** Implementar un fallback: si el modelo streamea, streamear; si no, esperar al JSON. El config-flow puede dejar al usuario elegir, o autodetectar en función del modelo seleccionado.

## Resolution path

Releer los hallazgos del ticket 01. Si la respuesta es (a) o (c), el cliente HTTP en `opencode_api/client.py` se construye alrededor de `client.post(..., stream=True)` con un parser SSE. Si es (b), se usa el path normal de `client.post(...)` y `await response.json()`. Documentar la decisión y la evidencia (un `curl --no-buffer` o un fragmento del código de la CLI `opencode` que muestre el shape del stream) en la resolución de este ticket.

## Skills to consult

- Hallazgos de `01-opencode-go-api-surface` (prerrequisito).
- `developers.home-assistant.io/docs/core/entity/conversation` para la API de streaming del `ChatLog`.

## Answer

Sí hay streaming; usamos SSE sobre `/responses` y traducimos `response.output_text.delta` / tool-call events a `ChatLog.async_add_delta_content_stream`.

## Comments

