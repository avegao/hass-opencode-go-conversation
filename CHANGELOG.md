# Changelog

## Unreleased

- Read the model catalog from `GET /models` at runtime and derive each model's
  endpoint from its `api` metadata instead of a hardcoded table.
- Removed the default model and the stale catalog snapshot: the model is now
  required during setup and always comes from the live catalog.
- Report models dropped from the OpenCode Go plan with an actionable error and
  refresh the catalog.
- Refresh the catalog during setup so the first conversation does not wait for
  it.

## 0.2.0

- Added model-aware routing and protocol-specific request/SSE adapters for the
  Responses, OpenAI-compatible, and Anthropic OpenCode Go endpoints.

## 0.1.0

- Initial OpenCode Go Conversation integration.
- Updated to current Home Assistant and tooling versions.
- Added OpenCode Go client identification, per-conversation session headers, and
  a bounded tool-call turn budget.
