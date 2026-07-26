Type: task
Status: resolved

## Question

Adaptar el `.devcontainer/` de `hass-codex-conversation` a este repo, para que un contenedor de VS Code (o similar) levante un Home Assistant completo con la integración ya cargada desde el código fuente.

Pasos:

1. Copiar `.devcontainer/` de la fuente a este repo.
2. Reemplazar todas las referencias a `opencode_go_conversation` por `opencode_go_conversation` (paths en `devcontainer.json`, `docker-compose.yml` o equivalente, scripts de bootstrap).
3. Verificar que el `Dockerfile` (o la imagen base) sigue siendo compatible con la versión de Home Assistant que estamos apuntando (`2026.3.0`).
4. Si la fuente usaba un usuario/contraseña o token hardcodeado para el devcontainer, dejarlo en `devcontainer.json` con el valor por defecto típico de las imágenes de HA para desarrollo (`dev`/`dev` o el que use la fuente).
5. Confirmar que el devcontainer puede correr `pytest` dentro del HA levantado (con `pytest-homeassistant-custom-component` configurado en `pyproject.toml`).
6. **No commitear todavía** — el usuario se encarga de los commits; dejar el árbol de trabajo listo.

## Acceptance criteria

- `code .` desde la raíz del repo abre VS Code, propone "Reopen in Container", y construye el contenedor sin errores.
- Dentro del contenedor, `pytest tests/` corre contra la instancia de Home Assistant del propio contenedor y los tests del config-flow (cuando se escriban, después de 05 + 06) pasan.
- La integración `OpenCode Go Conversation` aparece en **Settings → Devices & Services** del HA del devcontainer (aunque todavía no se pueda configurar por falta de código).

## Skills to consult

- Documentación de `devcontainer.json` y de las imágenes dev de Home Assistant.
- La fuente `hass-codex-conversation/.devcontainer/` como base.

## Answer

Devcontainer copiado y adaptado; nombre del contenedor, hooks y scripts de arranque apuntan al dominio `opencode_go_conversation`, y el post-attach ya no depende del blueprint original.

## Comments

