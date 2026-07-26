# Research: Home Assistant AI Task API (2026.x)

## Summary

Home Assistant’s AI Task integration currently exposes `AITaskEntity` with `generate_data` and `generate_image` entry points, but the source integration we are mirroring only implements data generation.

## Findings

### Entity contract

- `AITaskEntity` lives in `homeassistant/components/ai_task/entity.py`.
- The entity exposes two overridable methods:
  - `_async_generate_data(self, task: GenDataTask, chat_log: ChatLog) -> GenDataTaskResult`
  - `_async_generate_image(self, task: GenImageTask, chat_log: ChatLog) -> GenImageTaskResult`
- Core prepares a `ChatLog` for tasks by calling `async_get_chat_log(...)` and then `chat_log.async_provide_llm_data(...)`.
- For data tasks, core appends the user prompt with `chat_log.async_add_user_content(UserContent(task.instructions, attachments=task.attachments))`.

### Task shapes

- `GenDataTask` carries `name`, `instructions`, optional `structure`, optional `attachments`, and optional `llm_api`.
- `GenDataTaskResult` returns `conversation_id` and `data`.
- `AITaskEntityFeature` includes `GENERATE_DATA`, `SUPPORT_ATTACHMENTS`, and `GENERATE_IMAGE`.

### Current source behavior

- `hass-codex-conversation` only implements the data path; it has no `generate_image` implementation.
- The source’s `ai_task.py` imports only `OpenCodeGoClient` and `async_run_chat_log` for data generation.

## Implications for this integration

- We should mirror the source and implement `generate_data` only for the first release.
- `generate_image` should remain unsupported unless the Go backend unexpectedly provides a compatible image endpoint (not indicated by current docs).
- The subentry for AI Task can stay focused on model selection + prompt controls; no image-specific UI is needed.

## Sources

- https://github.com/home-assistant/core/blob/dev/homeassistant/components/ai_task/entity.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/ai_task/task.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/ai_task/const.py
- /Users/avegao/Develop/hass-codex-conversation/custom_components/opencode_go_conversation/ai_task.py
