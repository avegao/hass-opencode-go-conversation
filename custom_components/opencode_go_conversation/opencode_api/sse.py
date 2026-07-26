"""SSE transport layer for OpenCode Go chat-completions streaming."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import aiohttp

from .models import (
    FunctionCallAdded,
    FunctionCallArgumentsDone,
    OutputTextDelta,
    ResponseEvent,
)

_LOGGER = logging.getLogger(__name__)


# ── Error classification ───────────────────────────────────────────────────────


def _extract_tool_call(payload: dict[str, Any]) -> tuple[str, str, str]:
    """Return ``(call_id, name, arguments)`` for a streamed tool call delta."""
    call_id = str(payload.get("id") or "")
    function = payload.get("function") or {}
    name = str(function.get("name") or "")
    arguments = str(function.get("arguments") or "")
    return call_id, name, arguments


# ── Async SSE iterator ─────────────────────────────────────────────────────────


async def sse_iter(resp: aiohttp.ClientResponse) -> AsyncIterator[ResponseEvent]:
    """Iterate over chat-completions SSE and yield typed OpenCode events."""
    pending_calls: dict[int, dict[str, Any]] = {}
    async for raw_line in resp.content:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        data_str = line[5:].strip()
        if not data_str or data_str == "[DONE]":
            for item in pending_calls.values():
                if item.get("arguments") is not None:
                    yield FunctionCallArgumentsDone(
                        arguments=item["arguments"],
                        item_id=item["item_id"],
                    )
            pending_calls.clear()
            continue

        try:
            evt: dict[str, Any] = json.loads(data_str)
        except json.JSONDecodeError:
            _LOGGER.debug("opencode_api.sse: unparseable data payload: %.120s", data_str)
            continue

        choices = evt.get("choices") or []
        if not choices:
            continue

        choice = choices[0] or {}
        delta = choice.get("delta") or {}

        content = delta.get("content")
        if content:
            yield OutputTextDelta(delta=str(content), content_index=0)

        tool_calls = delta.get("tool_calls") or []
        for index, raw_tool_call in enumerate(tool_calls):
            if not isinstance(raw_tool_call, dict):
                continue
            call_id, name, arguments = _extract_tool_call(raw_tool_call)
            item = pending_calls.setdefault(
                index, {"call_id": call_id, "name": name, "item_id": call_id, "arguments": ""}
            )
            if call_id:
                item["call_id"] = call_id
                item["item_id"] = call_id
            if name:
                item["name"] = name
            if arguments:
                item["arguments"] = f"{item['arguments']}{arguments}"
            if item.get("call_id") and item.get("name"):
                yield FunctionCallAdded(
                    call_id=item["call_id"],
                    name=item["name"],
                    item_id=item["item_id"],
                )

        if choice.get("finish_reason") == "tool_calls":
            for index, item in list(pending_calls.items()):
                if item.get("arguments") is not None:
                    yield FunctionCallArgumentsDone(
                        arguments=item["arguments"],
                        item_id=item["item_id"],
                    )
                pending_calls.pop(index, None)
