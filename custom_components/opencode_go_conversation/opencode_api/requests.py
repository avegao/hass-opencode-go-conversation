"""Common request model used by the OpenCode Go protocol adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OpenCodeGoRequest:
    """Typed request before it is serialised for a model's API protocol."""

    model: str
    messages: list[dict[str, Any]]
    reasoning_effort: str = "medium"
    tools: list[dict[str, Any]] = field(default_factory=list)
    session_id: str | None = None
    input_items: list[dict[str, Any]] | None = None
    instructions: str = ""

    def to_body(self) -> dict[str, Any]:
        """Serialise using the OpenAI-compatible chat shape."""
        from .payloads import to_chat_body

        return to_chat_body(self)
