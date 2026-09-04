"""Tests for the integration manifest."""

from __future__ import annotations

import json
from pathlib import Path

MANIFEST_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "opencode_go_conversation"
    / "manifest.json"
)


def test_manifest_declares_runtime_openapi_dependency() -> None:
    """Home Assistant must install the dependency used by tool formatting."""
    manifest = json.loads(MANIFEST_PATH.read_text())

    assert any(
        requirement.split("==", maxsplit=1)[0] == "voluptuous-openapi"
        for requirement in manifest["requirements"]
    )
