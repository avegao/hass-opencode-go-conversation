# OpenCode Go Conversation

Una integración personalizada de [Home Assistant](https://www.home-assistant.io/) que trae los modelos de **OpenCode Go** a tu hogar inteligente como agente de conversación.

## Características

- Configuración con clave de API de OpenCode Go
- Integración con Assist / conversación de Home Assistant
- Soporte de AI Task para generación de datos estructurados
- Respuestas en streaming
- Conversaciones multi-turno con historial
- Selector de modelo basado en los modelos de OpenCode Go
- Identificación del cliente y cabeceras de sesión compatibles con OpenCode Go
- Estructura compatible con HACS
- Puedes volver a introducir la clave de API desde **Reconfigurar** sin reinstalar la integración.

## Requisitos

| Requisito | Detalles |
| --- | --- |
| Home Assistant | 2026.3.0 o superior |
| Suscripción | OpenCode Go |

## Notas

- Las peticiones de generación identifican la integración con un `User-Agent`
  explícito y envían un valor estable de `x-opencode-session` derivado del ID de
  conversación de Home Assistant, como exige OpenCode Go.
- Los modelos se leen del catálogo en vivo (`GET /models`) y se prefijan con
  `opencode-go/`. No hay lista de modelos hardcodeada ni modelo por defecto:
  elige uno del catálogo al configurar el agente.
- La ruta de cada modelo se deriva de la metadata `api` del catálogo: Responses
  usa `/responses`, los modelos compatibles con OpenAI usan `/chat/completions` y
  los compatibles con Anthropic usan `/messages`. El prefijo de Home Assistant se
  elimina antes de enviar la petición.
- Los modelos que el cliente todavía no sabe hablar (Google `generate-content`)
  se ocultan en lugar de generar peticiones inválidas.
- Si OpenCode Go quita un modelo de su plan, la integración muestra un error
  accionable y refresca el catálogo.
- No hay tráfico en segundo plano ni bucles automáticos de reintento; los turnos
  adicionales por llamadas a herramientas están limitados a 10 por interacción.
