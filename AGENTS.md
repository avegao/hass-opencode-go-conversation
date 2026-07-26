# Repository Guidelines

## Project Structure

This repository is a Home Assistant custom integration for OpenCode Go. Runtime code lives in `custom_components/opencode_go_conversation/`; keep Home Assistant entry points (`conversation.py`, `ai_task.py`, `config_flow.py`) separate from transport code under `opencode_api/`. Metadata and UI strings are in `manifest.json`, `strings.json`, and `translations/`. Tests are in `tests/`, development configuration is in `config/`, and reusable commands are in `script/`. HACS branding assets are in the integration’s `brand/` directory and at the repository root.

## Build, Test, and Development Commands

Set up the managed environment with `./script/setup/bootstrap` (or `uv sync --group dev`). Common commands:

- `./script/test` — run the configured pytest suite; add `--cov` for terminal coverage.
- `./script/lint` — apply Ruff formatting and safe autofixes.
- `./script/lint-check` — run formatting and Ruff checks without modifying files.
- `./script/type-check` — run `ty check`.
- `./script/hassfest` — validate the integration against Home Assistant rules.
- `./script/check` — run type, lint, spelling, and available hassfest checks.
- `./script/develop` — start Home Assistant with `config/` and the local integration on `PYTHONPATH`.

Use `uv` for Python dependencies and commands; do not install packages with `pip`, `npm`, `npx`, or `yarn`.

## Coding Style and Naming

Use Python 3.14-compatible code, four-space indentation, type annotations, and Google-style docstrings where needed. Ruff formats and lints the project with an 88-character line length and import sorting. Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; and descriptive `test_*.py` and `test_*` names. Keep code, comments, logs, and documentation in English.

## Testing Guidelines

Pytest with Home Assistant fixtures is configured through `pyproject.toml`; tests are discovered from `tests/` and coverage targets the integration package. Add regression tests for config flow, Conversation, AI Task, transport, and parsing changes. Run focused tests first, then `./script/test` and `./script/check` before submitting.

## Commits and Pull Requests

Recent history is brief and mixed, so use Conventional Commits for new work, such as `fix(api): handle streaming errors` or `feat(conversation): support tool calls`. PRs should explain the change, link an issue with `Fixes #<number>` when applicable, describe validation, and complete the checklist. Update tests and documentation when behavior or setup changes; include screenshots for relevant UI or branding changes.

## Security and Configuration

Never commit OpenCode Go API keys or real conversation fixtures. Use the Home Assistant config flow and local environment/configuration for credentials. Review changes to HTTP endpoints, authentication, model selection, and streamed tool calls for trust-boundary implications.
