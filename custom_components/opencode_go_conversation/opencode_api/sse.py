"""SSE transport layer for the OpenCode Go API protocols."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import aiohttp

from .errors import OpenCodeGoStreamError
from .models import (
    FunctionCallAdded,
    FunctionCallArgumentsDelta,
    FunctionCallArgumentsDone,
    OutputItemAdded,
    OutputItemDone,
    OutputTextDelta,
    ReasoningSummaryDelta,
    ResponseCompleted,
    ResponseCreated,
    ResponseEvent,
)

_LOGGER = logging.getLogger(__name__)


def _extract_tool_call(payload: dict[str, Any]) -> tuple[str, str, str]:
    """Return ``(call_id, name, arguments)`` for a streamed tool call delta."""
    call_id = str(payload.get("id") or "")
    function = payload.get("function") or {}
    name = str(function.get("name") or "")
    arguments = str(function.get("arguments") or "")
    return call_id, name, arguments


def _flush_chat_calls(
    pending_calls: dict[int, dict[str, Any]],
) -> list[ResponseEvent]:
    """Return completed tool-call events and clear the pending calls."""
    events: list[ResponseEvent] = []
    for item in pending_calls.values():
        events.append(
            FunctionCallArgumentsDone(
                arguments=str(item.get("arguments") or ""),
                item_id=str(item.get("item_id") or ""),
            )
        )
    pending_calls.clear()
    return events


async def _sse_records(
    resp: aiohttp.ClientResponse,
) -> AsyncIterator[tuple[str, str]]:
    """Yield complete ``(event, data)`` records from an SSE response."""
    event_name = ""
    data_lines: list[str] = []

    async for raw_line in resp.content:
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line:
            if data_lines:
                yield event_name, "\n".join(data_lines)
            event_name = ""
            data_lines.clear()
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    if data_lines:
        yield event_name, "\n".join(data_lines)


async def sse_iter(resp: aiohttp.ClientResponse) -> AsyncIterator[ResponseEvent]:
    """Iterate over OpenAI-compatible chat-completions SSE."""
    pending_calls: dict[int, dict[str, Any]] = {}
    async for _event_name, data_str in _sse_records(resp):
        if not data_str or data_str == "[DONE]":
            for event in _flush_chat_calls(pending_calls):
                yield event
            continue

        try:
            evt: dict[str, Any] = json.loads(data_str)
        except json.JSONDecodeError:
            _LOGGER.debug(
                "opencode_api.sse: unparseable data payload: %.120s", data_str
            )
            continue

        if isinstance(evt.get("error"), dict):
            raise OpenCodeGoStreamError(
                str(evt["error"].get("message") or evt["error"])
            )

        choices = evt.get("choices") or []
        if not choices:
            continue

        choice = choices[0] or {}
        delta = choice.get("delta") or {}

        content = delta.get("content")
        if content:
            yield OutputTextDelta(delta=str(content), content_index=0)

        tool_calls = delta.get("tool_calls") or []
        for fallback_index, raw_tool_call in enumerate(tool_calls):
            if not isinstance(raw_tool_call, dict):
                continue
            index = raw_tool_call.get("index", fallback_index)
            if not isinstance(index, int):
                index = fallback_index
            call_id, name, arguments = _extract_tool_call(raw_tool_call)
            item = pending_calls.setdefault(
                index,
                {
                    "call_id": call_id,
                    "name": name,
                    "item_id": call_id,
                    "arguments": "",
                    "announced": False,
                },
            )
            if call_id:
                item["call_id"] = call_id
                item["item_id"] = call_id
            if name:
                item["name"] = name
            if arguments:
                item["arguments"] = f"{item['arguments']}{arguments}"
            if item.get("call_id") and item.get("name") and not item["announced"]:
                item["announced"] = True
                yield FunctionCallAdded(
                    call_id=item["call_id"],
                    name=item["name"],
                    item_id=item["item_id"],
                )
            if arguments:
                yield FunctionCallArgumentsDelta(
                    delta=arguments,
                    item_id=item["item_id"],
                )

        if choice.get("finish_reason") == "tool_calls":
            for event in _flush_chat_calls(pending_calls):
                yield event


async def responses_sse_iter(
    resp: aiohttp.ClientResponse,
) -> AsyncIterator[ResponseEvent]:
    """Iterate over OpenAI Responses API SSE events."""
    async for event_name, data_str in _sse_records(resp):
        if data_str == "[DONE]":
            continue
        try:
            evt: dict[str, Any] = json.loads(data_str)
        except json.JSONDecodeError:
            _LOGGER.debug(
                "opencode_api.sse: unparseable Responses payload: %.120s", data_str
            )
            continue

        event_type = event_name or str(evt.get("type") or "")
        if event_type in ("error", "response.failed"):
            error = evt.get("error") or (evt.get("response") or {}).get("error")
            message = error.get("message") if isinstance(error, dict) else error
            raise OpenCodeGoStreamError(
                str(message or "OpenCode Go Responses stream failed")
            )
        if event_type == "response.created":
            response = evt.get("response") or {}
            if isinstance(response, dict) and response.get("id"):
                yield ResponseCreated(response_id=str(response["id"]))
        elif event_type == "response.output_item.added":
            item = evt.get("item") or {}
            if not isinstance(item, dict):
                continue
            yield OutputItemAdded(item=item)
            if item.get("type") == "function_call":
                call_id = str(item.get("call_id") or item.get("id") or "")
                name = str(item.get("name") or "")
                item_id = str(item.get("id") or call_id)
                if call_id and name:
                    yield FunctionCallAdded(call_id=call_id, name=name, item_id=item_id)
        elif event_type == "response.output_text.delta":
            delta = evt.get("delta")
            if isinstance(delta, str) and delta:
                yield OutputTextDelta(
                    delta=delta,
                    content_index=int(evt.get("content_index") or 0),
                )
        elif event_type == "response.reasoning_summary_text.delta":
            delta = evt.get("delta")
            if isinstance(delta, str) and delta:
                yield ReasoningSummaryDelta(
                    delta=delta,
                    summary_index=int(evt.get("summary_index") or 0),
                )
        elif event_type == "response.function_call_arguments.delta":
            delta = evt.get("delta")
            item_id = evt.get("item_id")
            if isinstance(delta, str) and isinstance(item_id, str):
                yield FunctionCallArgumentsDelta(delta=delta, item_id=item_id)
        elif event_type == "response.function_call_arguments.done":
            arguments = evt.get("arguments", "")
            item_id = evt.get("item_id")
            if isinstance(arguments, str) and isinstance(item_id, str):
                yield FunctionCallArgumentsDone(arguments=arguments, item_id=item_id)
        elif event_type == "response.output_item.done":
            item = evt.get("item") or {}
            if isinstance(item, dict):
                yield OutputItemDone(item=item)
        elif event_type == "response.completed":
            response = evt.get("response") or {}
            usage = response.get("usage", {}) if isinstance(response, dict) else {}
            yield ResponseCompleted(usage=usage if isinstance(usage, dict) else {})


async def anthropic_sse_iter(
    resp: aiohttp.ClientResponse,
) -> AsyncIterator[ResponseEvent]:
    """Iterate over Anthropic Messages API SSE events."""
    pending_calls: dict[int, dict[str, Any]] = {}
    usage: dict[str, Any] = {}

    async for _event_name, data_str in _sse_records(resp):
        if data_str == "[DONE]":
            continue
        try:
            evt: dict[str, Any] = json.loads(data_str)
        except json.JSONDecodeError:
            _LOGGER.debug(
                "opencode_api.sse: unparseable Anthropic payload: %.120s", data_str
            )
            continue

        event_type = str(evt.get("type") or "")
        if event_type == "error":
            error = evt.get("error")
            message = error.get("message") if isinstance(error, dict) else error
            raise OpenCodeGoStreamError(
                str(message or "OpenCode Go Anthropic stream failed")
            )
        if event_type == "message_start":
            message = evt.get("message") or {}
            if isinstance(message, dict):
                response_id = message.get("id")
                if response_id:
                    yield ResponseCreated(response_id=str(response_id))
                message_usage = message.get("usage")
                if isinstance(message_usage, dict):
                    usage.update(message_usage)
        elif event_type == "content_block_start":
            block = evt.get("content_block") or {}
            index = evt.get("index", 0)
            if not isinstance(index, int) or not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                call_id = str(block.get("id") or "")
                name = str(block.get("name") or "")
                pending_calls[index] = {"item_id": call_id, "arguments": ""}
                if call_id and name:
                    yield FunctionCallAdded(call_id=call_id, name=name, item_id=call_id)
        elif event_type == "content_block_delta":
            index = evt.get("index", 0)
            delta = evt.get("delta") or {}
            if not isinstance(index, int) or not isinstance(delta, dict):
                continue
            if delta.get("type") == "text_delta":
                text = delta.get("text")
                if isinstance(text, str) and text:
                    yield OutputTextDelta(delta=text, content_index=index)
            elif delta.get("type") == "input_json_delta":
                partial = delta.get("partial_json")
                item = pending_calls.get(index)
                if isinstance(partial, str) and item is not None:
                    item["arguments"] += partial
                    yield FunctionCallArgumentsDelta(
                        delta=partial,
                        item_id=item["item_id"],
                    )
        elif event_type == "content_block_stop":
            index = evt.get("index", 0)
            if isinstance(index, int):
                item = pending_calls.pop(index, None)
                if item is not None:
                    yield FunctionCallArgumentsDone(
                        arguments=item["arguments"],
                        item_id=item["item_id"],
                    )
        elif event_type == "message_delta":
            message_usage = evt.get("usage")
            if isinstance(message_usage, dict):
                usage.update(message_usage)
        elif event_type == "message_stop":
            for item in pending_calls.values():
                yield FunctionCallArgumentsDone(
                    arguments=item["arguments"],
                    item_id=item["item_id"],
                )
            pending_calls.clear()
            yield ResponseCompleted(usage=usage)
