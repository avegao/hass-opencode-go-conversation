"""Model-to-endpoint routing for the OpenCode Go API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .errors import OpenCodeGoError

MODEL_PREFIX = "opencode-go/"

ModelProtocol = Literal["responses", "chat", "anthropic"]


@dataclass(frozen=True, slots=True)
class ModelRoute:
    """Wire contract selected for one OpenCode Go model."""

    model_id: str
    protocol: ModelProtocol
    path: str


# Keep this table in the same order as the endpoint table in the OpenCode Go
# documentation (https://opencode.ai/docs/go/#endpoints). The API's /models
# response does not expose the protocol, so routing cannot be inferred safely
# from model names at runtime.
_RESPONSES_MODEL_IDS = (
    "grok-4.6",
    "gpt-5.6-luna",
    "muse-spark-1.3-contributor",
    "muse-spark-1.2-contributor",
)
_CHAT_MODEL_IDS = (
    "glm-5.3-flash",
    "glm-5.3",
    "glm-5.2",
    "glm-5.1",
    "kimi-k3",
    "kimi-k2.7-code",
    "kimi-k2.6",
    "longcat-2.0",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "deepseek-v4-flash-vision-exp",
    "mimo-v2.5",
    "mimo-v2.5-pro",
    "hy4-preview",
    "hy3",
    "omen-alpha",
    # Kept for existing Home Assistant configurations.  It is still present
    # in the live catalog although the current docs table recommends Grok 4.6.
    "grok-4.5",
)
_ANTHROPIC_MODEL_IDS = (
    "minimax-m3",
    "minimax-m2.7",
    "minimax-m2.5",
    "qwen3.8-max",
    "qwen3.8-flash",
    "qwen3.7-max",
    "qwen3.7-plus",
    "qwen3.6-plus",
)


def _build_routes() -> dict[str, ModelRoute]:
    routes: dict[str, ModelRoute] = {}
    for model_id in _RESPONSES_MODEL_IDS:
        routes[model_id] = ModelRoute(model_id, "responses", "/responses")
    for model_id in _CHAT_MODEL_IDS:
        routes[model_id] = ModelRoute(model_id, "chat", "/chat/completions")
    for model_id in _ANTHROPIC_MODEL_IDS:
        routes[model_id] = ModelRoute(model_id, "anthropic", "/messages")
    return routes


MODEL_ROUTES = _build_routes()


def normalize_model_id(model: str) -> str:
    """Return the API model ID from a Home Assistant or raw model value."""
    if not isinstance(model, str):
        raise OpenCodeGoError("OpenCode Go model must be a string")

    model_id = model.strip()
    if model_id.startswith(MODEL_PREFIX):
        model_id = model_id.removeprefix(MODEL_PREFIX)
    if not model_id:
        raise OpenCodeGoError("OpenCode Go model ID must not be empty")
    return model_id


def resolve_model_route(model: str) -> ModelRoute:
    """Resolve a model ID to its documented OpenCode Go wire protocol."""
    model_id = normalize_model_id(model)
    try:
        return MODEL_ROUTES[model_id]
    except KeyError as err:
        raise OpenCodeGoError(
            f"OpenCode Go does not have a known endpoint mapping for model "
            f"{model_id!r}; refresh the integration when OpenCode publishes "
            "the model's endpoint"
        ) from err


def supported_model_ids() -> tuple[str, ...]:
    """Return model IDs with a known endpoint mapping."""
    return tuple(MODEL_ROUTES)
