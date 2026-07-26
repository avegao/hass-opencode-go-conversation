"""
Request model for the OpenCode Go Responses API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OpenCodeGoRequest:
    """Typed request for the OpenCode Go ``/responses`` endpoint."""

    model: str
    input: list[dict[str, Any]]
    instructions: str = ""
    store: bool = False
    reasoning_effort: str = "medium"
    reasoning_summary: str = "auto"
    text_verbosity: str = "medium"
    tools: list[dict[str, Any]] = field(default_factory=list)

    def _include_reasoning(self) -> bool:
        return self.model.startswith("opencode-go/")

    def to_body(self) -> dict[str, Any]:
        """Serialise to the JSON body expected by the OpenCode Go endpoint."""
        body: dict[str, Any] = {
            "model": self.model,
            "stream": True,
            "store": self.store,
            "input": self.input,
        }
        if self.instructions:
            body["instructions"] = self.instructions
        if self.tools:
            body["tools"] = self.tools
        if self._include_reasoning():
            body["reasoning"] = {
                "effort": self.reasoning_effort,
                "summary": self.reasoning_summary,
            }
            body["text"] = {"verbosity": self.text_verbosity}
            body["include"] = ["reasoning.encrypted_content"]
        return body
