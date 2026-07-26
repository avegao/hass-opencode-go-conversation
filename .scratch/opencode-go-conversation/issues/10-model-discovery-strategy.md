Type: grilling
Status: resolved
Blocked by: 01

## Question

¿Cómo obtenemos la lista de modelos que se muestra en el `SelectSelector` del subentry "advanced"? ¿La hardcodeamos, la pedimos al backend dinámicamente, o las dos?

El contexto: la fuente tiene `MODELS = ["gpt-5.6-sol", "gpt-5.6-terra", ...]` hardcoded en `const.py`. Eso está bien porque los modelos de OpenCodeGo cambian poco. Pero OpenCode Go tiene un set de modelos más vivo (la página `/go` lista ~15 modelos: Grok 4.5, GLM-5.2, GLM-5.1, Kimi K3, Kimi K2.7 Code, Kimi K2.6, MiMo-V2.5-Pro, MiMo-V2.5, Qwen3.7 Max, Qwen3.7 Plus, Qwen3.6 Plus, MiniMax M2.7, MiniMax M3, DeepSeek V4 Pro, DeepSeek V4 Flash, Hy3), y OpenCode ya tiene fama de cambiar el catálogo con frecuencia.

Tres opciones a grillir:

- **(a) Hardcoded en `const.py` con la lista de `opencode.ai/go`.** Simple, sin red, mismo patrón que la fuente. Inconveniente: hay que bumpear versión cada vez que Go añade o quita un modelo. La integración queda "vieja" entre releases.
- **(b) Dinámico vía `GET /models` (o equivalente) en cada apertura del config-flow.** Lista siempre al día. Inconveniente: si el endpoint falla o el modelo ya no está disponible, el subentry queda en estado raro. Hay que cachear el resultado para no martillear el endpoint en cada render de la UI.
- **(c) Híbrido — hardcoded como fallback + endpoint `/models` en `__init__.py` que se llama al setup y se cachea en `hass.data`.** El subentry muestra la unión de hardcoded + dinámico, deduplicado, con los dinámicos marcados como "verificados". Más robusto. **Mi recomendación**, porque degrada con elegancia si el endpoint falla.

Decisiones adicionales que se cierran aquí:

- ¿Refrescamos la lista en cada reload de HA, o solo al setup inicial de la entry? **Mi recomendación**: setup inicial + un `async_track_time_interval` de 6-12h, configurable.
- ¿Mostramos solo los modelos disponibles para el tier del usuario (Go vs Go+ futuro), o la lista global? **Mi recomendación**: la lista global; el backend rechazará con 403/404 si el modelo no está en el tier, y ese error se muestra al usuario.
- ¿Modelos con capabilities distintas (texto, código, visión) marcados visualmente? Útil pero scope creep; lo dejamos para post-1.0.

## Resolution path

Releer los hallazgos del ticket 01. Si hay endpoint `/models`, implementar (c). Si no, caer a (a) con la lista de `opencode.ai/go`. Documentar la decisión y el snapshot de la lista en la fecha de release, más la URL de la página `/go` como source of truth, en la resolución de este ticket.

## Skills to consult

- Hallazgos de `01-opencode-go-api-surface` (prerrequisito).
- `developers.home-assistant.io/docs/core/entity/select` para el `SelectSelector` en el config-flow.

## Answer

Estrategia híbrida: lista dinámica desde `GET /models` con fallback a la snapshot de la documentación para que el selector siga funcionando si el endpoint falla.

## Comments

