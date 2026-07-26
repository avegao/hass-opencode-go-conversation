# Construir `hass-opencode-go-conversation`

## Destination

Un paquete HACS publicable en `~/Develop/hass-opencode-go-conversation` que replica `hass-codex-conversation` 1:1, sustituyendo OAuth2 device-flow por API key de OpenCode Go, exponiendo los modelos de la suscripción como agente de conversación de Home Assistant (y como `ai_task`) con streaming, multi-turn, selector dinámico de modelo, manifest válido, `hacs.json`, `info.md`, README bilingüe, tests verdes y un release tag listo para añadir como HACS Custom Repository desde la cuenta `avegao`.

## Notes

- **Dominio**: integración de Home Assistant / custom_component.
- **Skills que cada sesión debe consultar**:
  - Documentación oficial de desarrollo de Home Assistant (`developers.home-assistant.io`), en particular: `config_entries`, `config_flow` con subentries, `conversation` (incl. `ChatLog`, `AssistantContentDelta`, `llm` API), `ai_task` (`generate_data`, `generate_content`).
  - Documentación de OpenCode Go (`opencode.ai/go`, `opencode.ai/docs`) y el repo `github.com/anomalyco/opencode` (CLI/SDK) para la superficie del API.
  - Skill `grilling` y `domain-modeling` cuando una decisión esté ambigua.
- **Preferencias fijas del esfuerzo**:
  - Paridad 1:1 con `hass-codex-conversation` salvo auth (sin OAuth, sin refresh token, sin device flow).
  - Cliente HTTP: `aiohttp` vía `async_get_clientsession(self.hass)` (convención HA, la usa la fuente).
  - Tests: `pytest-homeassistant-custom-component`, snapshots de la conversación, mocks HTTP con `aioresponses` cuando no haya fixtures reales.
  - i18n: `strings.json` + `translations/{en,es}.json` mínimo.
  - Python ≥ 3.12, ruff, prettier para JSON/MD, pre-commit.
  - **El agente NO hace commits ni push** durante este esfuerzo. El usuario (`avegao`) se encarga de `git commit` / `git push` y de crear el repo público en GitHub bajo `avegao/hass-opencode-go-conversation`. El agente trabaja en el árbol de trabajo sin commitear.
  - Idioma: el mapa, los tickets y la conversación con el usuario en español. `README.md` y `info.md` en EN (y `README.es.md` si el usuario lo pide). `translations/` en `en` y `es`.
- **Convención Wayfinder del repo**: tracker local en `.scratch/opencode-go-conversation/`. Map = `map.md`. Tickets = `issues/NN-<slug>.md` numerados desde `01`.

## Decisions so far

- [OpenCode Go API surface](./issues/01-opencode-go-api-surface.md) — Go uses mixed OpenAI/Anthropic-compatible endpoints under `/zen/go/v1`, with Bearer or `x-api-key` auth, `GET /models`, and streaming on both chat endpoints.
- [HA conversation API 2026](./issues/02-ha-conversation-api-2026.md) — current conversation entities still use `_async_handle_message` and the modern `ChatLog`/subentry APIs.
- [HA AI Task API 2026](./issues/03-ha-ai-task-api-2026.md) — `AITaskEntity` still supports data/image entry points, but this integration should implement data only.
- [Scaffold the skeleton](./issues/05-scaffold-skeleton.md) — the component tree, manifests, strings, and `opencode_api/` package are in place.
- [Bootstrap the repo files](./issues/06-bootstrap-repo-files.md) — `pyproject.toml`, `README`, `CHANGELOG`, `hacs.json`, and lint/test metadata are aligned.
- [Bootstrap the devcontainer](./issues/07-bootstrap-devcontainer.md) — the devcontainer and attach hooks now point at `opencode_go_conversation`.
- [Reasoning controls applicability](./issues/08-reasoning-controls-applicability.md) — keep the source’s advanced reasoning fields because Go accepts reasoning controls.
- [Streaming shape](./issues/09-streaming-shape.md) — use SSE from `/responses` and translate OpenCode Go response events into HA delta content.
- [Model discovery strategy](./issues/10-model-discovery-strategy.md) — dynamically fetch `/models` with a docs-snapshot fallback.

## Not yet specified

- **Mapeo de errores del backend de Go → excepciones HA** (`ConfigEntryNotReady`, repair issues, `HomeAssistantError`, `ConverseError`). Falta el último pulido de cómo exponer errores transitorios frente a fallos de auth/cuota en la UI de HA.
- **Smoke test end-to-end en un Home Assistant real** (no devcontainer). Depende de (a) ticket 04 (tener API key real) y (b) que el usuario tenga un HA disponible para probar.

## Out of scope

- **Submitir el repo al HACS default repository** (proceso de revisión de inclusión). Queda para el usuario si lo decide tras publicarlo como Custom Repository.
- **Multi-cuenta / multi-tenant** (varios suscriptores de Go en una sola instalación de HA). No está en la fuente y se descarta por ahora.
- **Botón "top up credit" o display de uso** en la UI de HA. La fuente no lo tiene y no se ha pedido; queda descartado para esta iteración.
- **Reescritura de la fuente `hass-codex-conversation`** para soportar ambos backends con un flag. Sería scope creep que cambia el destino; el destino es un paquete independiente para Go.
