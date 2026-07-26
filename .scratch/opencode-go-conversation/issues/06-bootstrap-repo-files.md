Type: task
Status: resolved

## Question

Crear la metadata del repo en la raíz (configuración de linters, formatter, dependencias, ignores) para que `pytest`, `ruff`, `pre-commit` y `prettier` funcionen out-of-the-box.

Lista de archivos a crear, con la fuente como referencia (copiar y adaptar; no inventar):

- `pyproject.toml` — dependencias, ruff config, tool config para HA. Partir del de `hass-codex-conversation`; quitar `openai` (si lo tiene) o `codex` (no existe como paquete), mantener `homeassistant`, `pytest-homeassistant-custom-component`, `aiohttp`, `voluptuous`. Añadir cualquier SDK cliente que el ticket 01 determine (probablemente ninguno si el API es HTTP plano).
- `uv.lock` — regenerar con `uv sync` tras tocar `pyproject.toml`. **No commitear cambios no intencionales**: si solo se ha copiado, dejar el lock como esté hasta que se añadan deps nuevas.
- `.gitignore` — copiar del source; añadir `tests/.env` si el ticket 04 acaba usando ese método para la API key.
- `.editorconfig` — copiar tal cual del source.
- `.pre-commit-config.yaml` — copiar tal cual; verificar que las versiones de los hooks están actualizadas.
- `.prettierrc.yml` y `.prettierignore` — copiar tal cual; verifica que cubre `*.json`, `*.md`, `*.yaml`, `*.yml`.
- `.markdownlint.json` — copiar tal cual.
- `tests/__init__.py`, `tests/conftest.py` — `conftest.py` con un fixture mínimo que devuelva un `hass` mock para los tests, basado en lo que use la fuente.
- `tests/components/opencode_go_conversation/` — directorio vacío por ahora; se rellenará con `test_config_flow.py`, `test_init.py`, `test_conversation.py`, `test_ai_task.py` cuando esos archivos existan.
- `script/` — copiar `bootstrap`, `setup`, `lint`, `format`, `test` (o equivalentes) del source. Verificar que los shebangs y el path a `python` son correctos para este repo.
- `LICENSE` — MIT, con copyright del usuario. Se puede clonar del source y cambiar el nombre.
- `CHANGELOG.md` — placeholder inicial con una entrada `0.1.0 - TBD` que se actualizará al taggear.
- `README.md` y `README.es.md` — placeholders (`# OpenCode Go Conversation\n\nTBD`) por ahora; el contenido real se graduará cuando haya un esqueleto funcional.
- `hacs.json` — `{ "name": "OpenCode Go Conversation", "hacs": "0.0.1", "render_readme": true, "homeassistant": "2026.3.0" }`.
- `info.md` — placeholder; contenido real se graduará después.
- `.github/` — copiar workflows del source (CI, Dependabot si existe), ajustar nombres y paths.

## Acceptance criteria

- `uv sync` (o `pip install -e .`) instala sin errores.
- `pytest tests/` corre y, si no hay tests todavía, sale con `no tests ran` y exit code 5 (esperable) sin crashear.
- `ruff check .` y `ruff format --check .` pasan.
- `pre-commit run --all-files` pasa (o falla solo en archivos que no se han tocado todavía, sin errores nuevos).
- `prettier --check '**/*.{json,md,yml,yaml}'` pasa.
- El devcontainer (creado en el ticket 07) levanta y entra al entorno Python correcto.

## Skills to consult

- `developers.home-assistant.io/docs/creating_integration_manifest`
- HACS documentation sobre el formato de `hacs.json` y `info.md`.

## Answer

Metadata raíz preparada: `pyproject.toml`, `hacs.json`, `README.md`, `README.es.md`, `CHANGELOG.md`, `info.md`, `uv.lock` y la config de lint/test quedó alineada con la integración.

## Comments

