Type: research
Status: resolved

## Question

¿Cuál es la superficie HTTP del backend de OpenCode Go a la que tiene que llamar esta integración?

Necesitamos dejar contestadas, en un único documento de research, todas las preguntas que las decisiones de diseño (subentry flow, conversation agent, ai_task, streaming, errores, modelo, autenticación) están esperando:

- **Endpoint base**: ¿cuál es la URL del API de Go? (`https://api.opencode.ai/v1` o similar; o es host custom). ¿Es estable o cambia por deployment?
- **Autenticación**: ¿cómo se pasa la API key? Header (`Authorization: Bearer …`), header custom (`X-Api-Key`), query string, cookie. ¿Hay scopes? ¿La key identifica al suscriptor de Go o al workspace?
- **Listado de modelos**: ¿hay endpoint `GET /models` (estilo OpenAI)? Si no, ¿de dónde se obtiene la lista? (¿hardcoded en la página `/go`? ¿en un manifest? ¿en el código de la CLI `opencode`?)
- **Chat / completions**: endpoint para enviar prompts (estilo `POST /v1/chat/completions` OpenAI-compatible, o estilo Anthropic `/v1/messages`, o custom). Payload exacto: system / user / assistant / tool messages, `tools`, `tool_choice`, `temperature`, `top_p`, `max_tokens`, `stream`, `reasoning_effort` (¿lo soporta?), `response_format` (structured output / JSON schema).
- **Respuesta**: ¿vuelve un único JSON o es streaming? Si streaming, ¿es SSE con `data: {...}\n\n` (estilo OpenAI) o NDJSON o chunked HTTP distinto? ¿Cómo se señaliza el final (`data: [DONE]`, `event: ...`, etc.)?
- **Errores**: códigos HTTP, cuerpo de error (¿`{"error": {"message": ..., "type": ...}}` estilo OpenAI?), rate-limit headers (`Retry-After`, `X-RateLimit-*`), clases de error que la fuente actual no contempla (cuota agotada, key inválida, modelo no disponible para el tier, etc.).
- **Rate limits y cuotas**: ¿el backend devuelve headers con el saldo restante? ¿hay un endpoint de "whoami" o "usage" para mostrar en la UI de HA?
- **Compatibilidad con el formato OpenAI**: ¿el endpoint es totalmente OpenAI-compatible, o se desvia en mensajes / tools / streaming? Si es OpenAI-compatible, el código se acorta mucho (podemos reusar el `openai` Python SDK contra esa base URL). Si no, hay que escribir cliente a mano.

## Resolution path

Capturar los hallazgos en una branch `research/opencode-go-api-surface` del repo (sin commitear — dejar el árbol de trabajo para que el usuario commitee), y dejar un puntero de contexto desde este ticket. Fuentes esperadas, en orden de prioridad:

1. `opencode.ai/docs` y `opencode.ai/go` (página oficial de la suscripción).
2. El repo `github.com/anomalyco/opencode` — la CLI y el SDK. Inspeccionar `packages/opencode/src/` o equivalente para ver las llamadas HTTP que ya hace la herramienta oficial.
3. Si el endpoint es OpenAI-compatible, un `curl` documentado con la API key (placeholder) para validar headers y shape.

Cuando cierre, este ticket desbloquea 08, 09, 10 y el resto de trabajo de implementación que pende del modelo de API.

## Skills to consult

- Documentación oficial de OpenCode Go.
- `github.com/anomalyco/opencode` (código fuente de la CLI).

## Answer

OpenCode Go exposes a mixed API surface under `https://opencode.ai/zen/go/v1`:

- **Auth**: `Authorization: Bearer <api_key>` for OpenAI-compatible endpoints, and `x-api-key: <api_key>` for Anthropic-compatible endpoints.
- **Endpoints**:
  - `POST /chat/completions` — OpenAI-compatible (`oa-compat`), used by Grok 4.5, GLM-5.2, GLM-5.1, Kimi K3, Kimi K2.7 Code, Kimi K2.6, DeepSeek V4 Pro, DeepSeek V4 Flash, MiMo-V2.5, MiMo-V2.5-Pro, and Hy3.
  - `POST /messages` — Anthropic-compatible, used by MiniMax M3/M2.7/M2.5 and Qwen3.7 Max/Plus + Qwen3.6 Plus.
  - `POST /responses` — OpenAI Responses API.
  - `GET /models` — returns an OpenAI-style `object: "list"` payload with the catalog.
- **Streaming**: supported on both `chat/completions` and `messages` (`stream: true`).
- **Body fields**:
  - OpenAI-compatible: `model`, `max_tokens`, `temperature`, `top_p`, `stop`, `messages`, `stream`, `tools`, `tool_choice`.
  - Anthropic-compatible: Anthropic `messages` shape, `anthropic-version: 2023-06-01`.
- **Reasoning controls**: supported by both helpers through the normalized `variant` parser; `reasoning_effort` / `reasoningEffort` is accepted on the OpenAI-compatible path and `effort` / `thinking.effort` / `output_config.effort` on the Anthropic-compatible path.

Implication for the integration: we need an internal router that chooses the right endpoint/header pair by model family, but the unified model catalog and API-key auth are straightforward.

## Comments

