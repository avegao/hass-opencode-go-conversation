# Research: OpenCode Go API surface

## Summary

OpenCode Go exposes a small set of documented endpoints under `https://opencode.ai/zen/go/v1`. For our Home Assistant integration, the important facts are:

- Auth is API-key based.
- OpenAI-style models use `POST /chat/completions` with `Authorization: Bearer <key>`.
- Anthropic-style models use `POST /messages` with `x-api-key: <key>` and `anthropic-version: 2023-06-01`.
- OpenAI Responses-style access exists at `POST /responses` with the same Bearer auth.
- `GET /models` returns the model catalog in OpenAI `object: list` format.
- Streaming is supported for both chat and messages endpoints via `stream: true`.
- The backend already normalizes reasoning controls; `parseOpenAiVariant` reads `reasoningEffort` / `reasoning_effort` / `reasoning.effort`, and `parseAnthropicVariant` reads `effort` / `output_config.effort` / `thinking.effort`.

## Findings

### Auth

- OpenCode docs: Go says you subscribe in Zen, copy the API key, and paste it in OpenCode.
- Server code:
  - `chat/completions` parses `headers.get("authorization")?.split(" ")[1]`.
  - `messages` parses `headers.get("x-api-key")`.
  - `responses` also parses `authorization` Bearer.

### Endpoints

- `https://opencode.ai/zen/go/v1/chat/completions` → OpenAI-compatible (`oa-compat`)
- `https://opencode.ai/zen/go/v1/messages` → Anthropic-compatible
- `https://opencode.ai/zen/go/v1/responses` → OpenAI Responses API
- `https://opencode.ai/zen/go/v1/models` → model list

### Model families

Docs list these current Go models:
Grok 4.5, GLM-5.2, GLM-5.1, Kimi K3, Kimi K2.7 Code, Kimi K2.6, MiMo-V2.5, MiMo-V2.5-Pro, MiniMax M3, MiniMax M2.7, MiniMax M2.5, Qwen3.7 Max, Qwen3.7 Plus, Qwen3.6 Plus, DeepSeek V4 Pro, DeepSeek V4 Flash, Hy3.

The docs map them like this:

- OpenAI-compatible: Grok 4.5, GLM-5.2, GLM-5.1, Kimi K3, Kimi K2.7 Code, Kimi K2.6, DeepSeek V4 Pro, DeepSeek V4 Flash, MiMo-V2.5, MiMo-V2.5-Pro, Hy3
- Anthropic-compatible: MiniMax M3, MiniMax M2.7, MiniMax M2.5, Qwen3.7 Max, Qwen3.7 Plus, Qwen3.6 Plus

### Streaming and request shape

The OpenAI-compatible provider adds `stream_options: { include_usage: true }` when `stream: true` is set.
The OpenAI-compatible body accepts `model`, `max_tokens`, `temperature`, `top_p`, `stop`, `messages`, `stream`, `tools`, and `tool_choice`.
The Anthropic-compatible body uses `x-api-key` and the standard Anthropic `messages` shape.

### Implications for this integration

- We need an internal router that selects the wire format by model family.
- The config-flow model selector should probably show the unified Go model catalog, but the client must branch to the right endpoint/header pair.
- `reasoning_effort` is supported by Go; the integration can keep a reasoning control in line with the source.

## Sources

- https://opencode.ai/docs/go
- https://opencode.ai/docs/providers
- https://github.com/anomalyco/opencode/blob/dev/packages/console/app/src/routes/zen/go/v1/chat/completions.ts
- https://github.com/anomalyco/opencode/blob/dev/packages/console/app/src/routes/zen/go/v1/messages.ts
- https://github.com/anomalyco/opencode/blob/dev/packages/console/app/src/routes/zen/go/v1/models.ts
- https://github.com/anomalyco/opencode/blob/dev/packages/console/app/src/routes/zen/go/v1/responses.ts
- https://github.com/anomalyco/opencode/blob/dev/packages/console/app/src/routes/zen/util/modelsHandler.ts
- https://github.com/anomalyco/opencode/blob/dev/packages/console/app/src/routes/zen/util/provider/openai-compatible.ts
- https://github.com/anomalyco/opencode/blob/dev/packages/console/app/src/routes/zen/util/provider/anthropic.ts
- https://github.com/anomalyco/opencode/blob/dev/packages/console/app/src/routes/zen/util/variant.ts
- https://github.com/anomalyco/opencode/blob/dev/packages/console/app/src/routes/zen/util/error.ts
