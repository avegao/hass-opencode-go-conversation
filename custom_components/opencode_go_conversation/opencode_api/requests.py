"""Request model for the OpenCode Go Chat Completions API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OpenCodeGoRequest:
    """Typed request for the OpenCode Go ``/chat/completions`` endpoint."""

    model: str
    messages: list[dict[str, Any]]
    reasoning_effort: str = "medium"
    tools: list[dict[str, Any]] = field(default_factory=list)

    def to_body(self) -> dict[str, Any]:
        """Serialise to the JSON body expected by the OpenCode Go endpoint."""
        body: dict[str, Any] = {
            "model": self.model,
            "stream": True,
            "messages": self.messages,
        }
        if self.tools:
            body["tools"] = self.tools
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        return body
