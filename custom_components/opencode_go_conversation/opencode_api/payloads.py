"""Serialisers for the three OpenCode Go request protocols."""

from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any

from .errors import OpenCodeGoError
from .requests import OpenCodeGoRequest
from .routing import normalize_model_id

_DATA_URL_RE = re.compile(r"^data:(?P<media_type>[^;]+);base64,(?P<data>.+)$")


def _as_data_url(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("url"), str):
        return value["url"]
    return None


def _chat_content(content: Any) -> Any:
    """Convert our input content parts to OpenAI-compatible chat parts."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return content

    parts: list[dict[str, Any]] = []
    for raw_part in content:
        if not isinstance(raw_part, dict):
            continue
        part_type = raw_part.get("type")
        if part_type in ("text", "input_text") and isinstance(
            raw_part.get("text"), str
        ):
            parts.append({"type": "text", "text": raw_part["text"]})
            continue
        if part_type == "input_image":
            image_url = _as_data_url(raw_part.get("image_url"))
            if image_url:
                parts.append({"type": "image_url", "image_url": {"url": image_url}})
            continue
        if part_type == "input_file":
            raise OpenCodeGoError(
                "The selected OpenCode Go chat model does not support PDF input"
            )

    if len(parts) == 1 and parts[0]["type"] == "text":
        return parts[0]["text"]
    return parts


def _chat_messages(request: OpenCodeGoRequest) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for raw_message in request.messages:
        if not isinstance(raw_message, dict):
            continue
        message = dict(raw_message)
        if "content" in message:
            message["content"] = _chat_content(message["content"])
        messages.append(message)
    return messages


def _chat_tools(request: OpenCodeGoRequest) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for raw_tool in request.tools:
        if not isinstance(raw_tool, dict):
            continue
        if raw_tool.get("type") != "function":
            tools.append(deepcopy(raw_tool))
            continue
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": raw_tool.get("name", ""),
                    "description": raw_tool.get("description", ""),
                    "parameters": raw_tool.get("parameters", {}),
                },
            }
        )
    return tools


def to_chat_body(request: OpenCodeGoRequest) -> dict[str, Any]:
    """Serialise a request for ``POST /chat/completions``."""
    body: dict[str, Any] = {
        "model": normalize_model_id(request.model),
        "stream": True,
        "messages": _chat_messages(request),
        "stream_options": {"include_usage": True},
    }
    if request.tools:
        body["tools"] = _chat_tools(request)
    if request.reasoning_effort:
        body["reasoning_effort"] = request.reasoning_effort
    return body


def _response_content(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"type": "input_text", "text": content}]
    if not isinstance(content, list):
        return []

    parts: list[dict[str, Any]] = []
    for raw_part in content:
        if not isinstance(raw_part, dict):
            continue
        part_type = raw_part.get("type")
        if part_type in ("text", "input_text") and isinstance(
            raw_part.get("text"), str
        ):
            parts.append({"type": "input_text", "text": raw_part["text"]})
        elif part_type in ("input_image", "input_file"):
            parts.append(deepcopy(raw_part))
    return parts


def _messages_to_response_items(request: OpenCodeGoRequest) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw_message in request.messages:
        if not isinstance(raw_message, dict):
            continue
        role = raw_message.get("role")
        content = raw_message.get("content")
        if role in ("system", "user"):
            response_content = _response_content(content)
            if response_content:
                items.append(
                    {"type": "message", "role": role, "content": response_content}
                )
        elif role == "assistant":
            if isinstance(content, str) and content:
                items.append(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": content}],
                    }
                )
            for raw_call in raw_message.get("tool_calls", []):
                if not isinstance(raw_call, dict):
                    continue
                function = raw_call.get("function") or {}
                if not isinstance(function, dict):
                    continue
                arguments = function.get("arguments", "{}")
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments)
                items.append(
                    {
                        "type": "function_call",
                        "call_id": raw_call.get("id", ""),
                        "name": function.get("name", ""),
                        "arguments": arguments,
                    }
                )
        elif role == "tool":
            output = raw_message.get("content", "")
            if not isinstance(output, str):
                output = json.dumps(output)
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": raw_message.get("tool_call_id", ""),
                    "output": output,
                }
            )
    return items


def to_responses_body(request: OpenCodeGoRequest) -> dict[str, Any]:
    """Serialise a request for ``POST /responses``."""
    body: dict[str, Any] = {
        "model": normalize_model_id(request.model),
        "stream": True,
        "input": deepcopy(
            request.input_items
            if request.input_items is not None
            else _messages_to_response_items(request)
        ),
    }
    if request.instructions:
        body["instructions"] = request.instructions
    if request.tools:
        body["tools"] = deepcopy(request.tools)
    if request.reasoning_effort:
        body["reasoning"] = {"effort": request.reasoning_effort}
    return body


def _anthropic_source(part: dict[str, Any]) -> dict[str, Any] | None:
    source_url = _as_data_url(part.get("image_url"))
    if not source_url:
        source_url = _as_data_url(part.get("file_data"))
    if not source_url:
        return None
    match = _DATA_URL_RE.match(source_url)
    if match:
        return {
            "type": "base64",
            "media_type": match.group("media_type"),
            "data": match.group("data"),
        }
    return {"type": "url", "url": source_url}


def _anthropic_content(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if not isinstance(content, list):
        return []

    parts: list[dict[str, Any]] = []
    for raw_part in content:
        if not isinstance(raw_part, dict):
            continue
        part_type = raw_part.get("type")
        if part_type in ("text", "input_text") and isinstance(
            raw_part.get("text"), str
        ):
            parts.append({"type": "text", "text": raw_part["text"]})
        elif part_type == "input_image":
            source = _anthropic_source(raw_part)
            if source:
                parts.append({"type": "image", "source": source})
        elif part_type == "input_file":
            source = _anthropic_source(raw_part)
            if source:
                parts.append({"type": "document", "source": source})
    return parts


def _anthropic_messages(request: OpenCodeGoRequest) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    messages: list[dict[str, Any]] = []
    for raw_message in request.messages:
        if not isinstance(raw_message, dict):
            continue
        role = raw_message.get("role")
        content = raw_message.get("content")
        if role == "system":
            if isinstance(content, str) and content:
                system_parts.append(content)
            continue
        if role == "user":
            parts = _anthropic_content(content)
            if parts:
                messages.append({"role": "user", "content": parts})
        elif role == "assistant":
            parts = _anthropic_content(content)
            for raw_call in raw_message.get("tool_calls", []):
                if not isinstance(raw_call, dict):
                    continue
                function = raw_call.get("function") or {}
                if not isinstance(function, dict):
                    continue
                arguments = function.get("arguments", "{}")
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        pass
                parts.append(
                    {
                        "type": "tool_use",
                        "id": raw_call.get("id", ""),
                        "name": function.get("name", ""),
                        "input": arguments,
                    }
                )
            if parts:
                messages.append({"role": "assistant", "content": parts})
        elif role == "tool":
            output = raw_message.get("content", "")
            if not isinstance(output, str):
                output = json.dumps(output)
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": raw_message.get("tool_call_id", ""),
                            "content": output,
                        }
                    ],
                }
            )
    return "\n\n".join(system_parts), messages


def to_anthropic_body(request: OpenCodeGoRequest) -> dict[str, Any]:
    """Serialise a request for ``POST /messages``."""
    system, messages = _anthropic_messages(request)
    if request.instructions and request.instructions not in system:
        system = "\n\n".join(part for part in (system, request.instructions) if part)

    body: dict[str, Any] = {
        "model": normalize_model_id(request.model),
        "max_tokens": 32_000,
        "messages": messages,
        "stream": True,
    }
    if system:
        body["system"] = system
    if request.tools:
        body["tools"] = [
            {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "input_schema": tool.get("parameters", {}),
            }
            for tool in request.tools
            if isinstance(tool, dict) and tool.get("type") == "function"
        ]
    if request.reasoning_effort:
        body["output_config"] = {"effort": request.reasoning_effort}
    return body
