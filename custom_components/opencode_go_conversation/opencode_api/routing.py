"""Model-to-endpoint routing derived from the OpenCode Go model catalog."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Literal

from .errors import OpenCodeGoError, OpenCodeGoModelNotInGo

MODEL_PREFIX = "opencode-go/"

ModelProtocol = Literal["responses", "chat", "anthropic"]

# How long a fetched catalog is reused before asking the API again.
CATALOG_TTL = 3600.0

# ``api`` keys published by ``GET /models`` mapped to the wire contract this
# client can serialise.  The catalog also publishes ``generate-content``
# (Google's protocol); models that only expose it are hidden from the picker
# until the client supports that endpoint.
_API_ROUTES: dict[str, tuple[ModelProtocol, str]] = {
    "chat-completions": ("chat", "/chat/completions"),
    "responses": ("responses", "/responses"),
    "messages": ("anthropic", "/messages"),
}


@dataclass(frozen=True, slots=True)
class ModelRoute:
    """Wire contract selected for one OpenCode Go model."""

    model_id: str
    protocol: ModelProtocol
    path: str


class ModelCatalog:
    """Cached view of the models and endpoints published by OpenCode Go."""

    def __init__(self, ttl: float = CATALOG_TTL) -> None:
        self._ttl = ttl
        self._routes: dict[str, ModelRoute] = {}
        self._fetched_at: float | None = None

    def update(self, payload: Any) -> None:
        """Replace the cache with the ``/models`` response *payload*."""
        entries = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            raise OpenCodeGoError(
                "OpenCode Go returned an unexpected model catalog response"
            )

        routes: dict[str, ModelRoute] = {}
        for entry in entries:
            route = route_from_catalog_entry(entry)
            if route is not None:
                routes[route.model_id] = route

        self._routes = routes
        self._fetched_at = time.monotonic()

    def replace(self, routes: dict[str, ModelRoute]) -> None:
        """Seed the cache directly, mainly for tests."""
        self._routes = dict(routes)
        self._fetched_at = time.monotonic()

    def reset(self) -> None:
        """Forget every cached model."""
        self._routes = {}
        self._fetched_at = None

    def invalidate(self) -> None:
        """Mark the cache stale so the next request fetches it again."""
        self._fetched_at = None

    @property
    def is_fresh(self) -> bool:
        """Return True while the cached catalog is still usable."""
        if self._fetched_at is None:
            return False
        return (time.monotonic() - self._fetched_at) < self._ttl

    def get(self, model_id: str) -> ModelRoute | None:
        """Return the route for *model_id*, if it is in the catalog."""
        return self._routes.get(model_id)

    @property
    def ids(self) -> tuple[str, ...]:
        """Return the model IDs that this client can talk to."""
        return tuple(self._routes)


MODEL_CATALOG = ModelCatalog()


def route_from_catalog_entry(entry: Any) -> ModelRoute | None:
    """Build a route from one entry of the ``/models`` catalog.

    Returns ``None`` for entries the client cannot serialise (for example
    models that only expose ``generate-content``).
    """
    if not isinstance(entry, dict):
        return None

    model_id = entry.get("id")
    if not isinstance(model_id, str) or not model_id.strip():
        return None

    api = entry.get("api")
    if not isinstance(api, dict):
        return None

    for api_name, (protocol, path) in _API_ROUTES.items():
        if api_name in api:
            return ModelRoute(model_id.strip(), protocol, path)

    return None


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
    """Resolve a model ID against the most recently fetched catalog."""
    model_id = normalize_model_id(model)
    route = MODEL_CATALOG.get(model_id)
    if route is None:
        raise OpenCodeGoModelNotInGo(
            f"Model {model_id!r} is not part of the current OpenCode Go "
            "catalog. Reload the integration options and pick a model from "
            "the refreshed list."
        )
    return route
