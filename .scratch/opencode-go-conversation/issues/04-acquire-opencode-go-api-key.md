Type: task
Status: open

## Question

Conseguir una API key real de OpenCode Go y dejarla accesible al agente para los smoke tests.

Pasos concretos (lo que tiene que hacer el usuario, no el agente):

1. Suscribirse a OpenCode Go en `opencode.ai/go` (botón "Subscribe to Go" → $5 primer mes, $10/mes después). Es inevitable para tener key real: OpenCode Go no expone tier free con API key.
2. Una vez dentro del dashboard, generar la API key. El propio sitio documenta el flujo: `Sign in, add your billing details, and copy your API key`.
3. Decidir dónde guardarla para que el agente pueda usarla en tests sin que quede en texto plano en el repo. Opciones a resolver **durante** este ticket, no ahora:
   - Variable de entorno en el devcontainer (`OPENCODE_GO_API_KEY=...` en `.env` no commiteado).
   - 1Password CLI (`op read "op://Personal/OpenCode Go/api key"`).
   - Fichero `tests/.env` con `.env` en `.gitignore` (el devcontainer ya tiene un `.devcontainer/.env` típico en este tipo de proyectos).
4. Confirmar que la key funciona haciendo un `curl` mínimo documentado:
   - `GET https://<endpoint>/models` (o el endpoint equivalente) con `Authorization: Bearer $KEY`.
   - Verificar que devuelve 200 y al menos un modelo.
   - Pegar la respuesta en el comentario de resolución de este ticket (sanitizando la key si aparece en headers).

## Acceptance criteria

- El usuario tiene una API key válida de OpenCode Go.
- Esa key está guardada en un sitio acordado con el agente y no en texto plano commiteado.
- Hay un `curl` documentado con su respuesta (sanitizada) que prueba que la key funciona contra el endpoint de Go. Esto sirve como ground truth para el ticket 01 cuando valide la superficie del API.
- Este ticket está `Status: resolved` y el mapa lo referencia desde `## Decisions so far`.

## Skills to consult

- `opencode.ai/go` y `opencode.ai/docs` (página de Go de la propia web).

## Comments

