Type: grilling
Status: resolved
Blocked by: 01

## Question

¿Tiene sentido mantener en la nueva integración los controles `reasoning_effort`, `reasoning_summary` y `text_verbosity` que `hass-codex-conversation` expone en su subentry "advanced", o hay que sustituirlos por el set más estándar (`temperature`, `top_p`, `max_tokens`)?

El contexto: la fuente expone tres controles que son específicos del backend de OpenCodeGo (OpenAI Responses API):

- `reasoning_effort` ∈ {`low`, `medium`, `high`} — controla cuánto "piensa" el modelo.
- `reasoning_summary` ∈ {`auto`, `short`, `detailed`, `off`} — verbosidad del resumen del razonamiento interno.
- `text_verbosity` ∈ {`low`, `medium`, `high`} — concisión de la respuesta final.

OpenCode Go expone otro set de modelos (Grok 4.5, GLM-5.2, Kimi K3, etc.) que puede o no soportar estos campos. Mi corazonada es que **no** los soportan (son específicos de la Responses API de OpenAI), y que la API estándar de chat completions (estilo OpenAI Chat Completions, que es lo que probablemente usa Go) acepta `temperature`, `top_p`, `max_tokens`, `presence_penalty`, `frequency_penalty`, `stop`, etc.

Tres opciones a grillir:

- **(a) Mantener los tres controles de la fuente tal cual.** Riesgo: si Go no los soporta, el backend los ignora silenciosamente y el usuario cree que está configurando algo que no aplica. Falso sentido de control.
- **(b) Sustituir los tres por `temperature`, `top_p`, `max_tokens`.** Pierde paridad 1:1 con la fuente, pero gana claridad y la config funciona en todos los modelos de Go. **Mi recomendación**, salvo que la investigación del ticket 01 revele que Go sí soporta los tres controles.
- **(c) Ofrecer ambos sets, con un toggle "usar controles avanzados estilo Responses API" que muestra los unos o los otros según el modelo.** Más rico pero añade complejidad al config-flow. Descartado por ahora, dejarlo como mejora post-1.0.

El ticket 01 traerá la respuesta técnica. Este grilling cierra la decisión de UX en función de eso.

## Resolution path

Releer los hallazgos del ticket 01 y elegir entre (a), (b) o (c) sabiendo ya qué soporta el backend. Si la respuesta es (a) o (b), el subentry "advanced" se ajusta en consecuencia. Documentar la decisión y la justificación (qué soporta Go, qué se descartaría) en la resolución de este ticket.

## Skills to consult

- Hallazgos de `01-opencode-go-api-surface` (prerrequisito).
- `developers.home-assistant.io` para el config-flow de subentries (cómo mostrar/ocultar campos).

## Answer

Mantener `reasoning_effort`, `reasoning_summary` y `text_verbosity`. Go soporta reasoning controls y el backend acepta el bloque `reasoning`; se conservan los controles avanzados de la fuente.

## Comments

