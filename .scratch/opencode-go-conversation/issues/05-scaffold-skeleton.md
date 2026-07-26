Type: task
Status: resolved

## Question

Crear el esqueleto de `custom_components/opencode_go_conversation/` con los archivos vacíos y la metadata correcta, para que el resto del trabajo de implementación tenga un lugar donde escribir.

Estructura objetivo (espejo de `opencode_go_conversation`, con los cambios que aplican):

```
custom_components/opencode_go_conversation/
├── __init__.py                 # sin OAuth, sin async_register_implementation
├── ai_task.py                  # stub
├── config_flow.py              # API-key form + subentries, sin device flow
├── const.py                    # DOMAIN, MODELS inicial vacío, defaults
├── conversation.py             # stub
├── manifest.json               # sin dependency "auth"
├── strings.json                # título, paso del config-flow, mensajes de error
├── translations/
│   ├── en.json
│   └── es.json
├── brand/
│   ├── icon.png                # placeholder; reemplazar cuando haya logo
│   └── icon@2x.png
├── opencode_api/               # antes opencode_api/
│   ├── __init__.py
│   ├── client.py               # stub
│   ├── errors.py               # jerarquía de errores nueva
│   ├── models.py               # request/response models
│   ├── requests.py             # request builders
│   └── sse.py                  # streaming parser
└── (NO oauth.py — el de la fuente desaparece)
```

Decisiones ya fijadas en el mapa (no se re-grillan aquí):

- **Domain**: `opencode_go_conversation`.
- **Display name**: "OpenCode Go Conversation".
- **iot_class**: `cloud_polling` (igual que la fuente).
- **dependencies** en `manifest.json`: `["ai_task", "conversation"]` (la fuente tenía `"auth"`; se quita).
- **version** en `manifest.json`: `0.1.0`.
- **codeowners**: `["@avegao"]`.
- **homeassistant**: `"2026.3.0"`.

Decisiones que **no** se toman en este ticket y se difieren a grilling/research:

- Lista de `MODELS` en `const.py`: vacía por ahora; se rellenará cuando el ticket 10 (model discovery) cierre.
- Contenido real de los stubs de `client.py`, `requests.py`, etc.: llega en tickets posteriores que dependen de 01.

## Acceptance criteria

- Todos los archivos listados existen en el árbol de trabajo, con stubs mínimos (un `pass` o un `"""TODO"""` en los `.py`).
- `manifest.json` es JSON válido y se puede instalar vía HACS como Custom Repository (aunque no haga nada todavía).
- `strings.json` y `translations/en.json` y `translations/es.json` son JSON válido y pasan el linter (`prettier --check`).
- El árbol compila sin errores de import (`python -c "import custom_components.opencode_go_conversation.const"` funciona).

## Skills to consult

- `developers.home-assistant.io/docs/creating_integration_manifest`
- `developers.home-assistant.io/docs/config_entries_config_flow_handler`
- `developers.home-assistant.io/docs/core/entity/conversation` (estructura mínima)

## Answer

Esqueleto creado: `custom_components/opencode_go_conversation/` con `__init__.py`, `config_flow.py`, `conversation.py`, `ai_task.py`, `opencode_api/`, `manifest.json`, `strings.json`, `translations/en.json` y `translations/es.json`. OAuth eliminado; dominio y nombres renombrados; listos para seguir iterando.

## Comments

