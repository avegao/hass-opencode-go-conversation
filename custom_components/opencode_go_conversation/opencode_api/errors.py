"""
OpenCodeGo API error hierarchy.

Adapted from the upstream OpenCode Go API error taxonomy.
"""

from __future__ import annotations


class OpenCodeGoError(Exception):
    """Base exception for all OpenCodeGo API errors."""


class OpenCodeGoApiError(OpenCodeGoError):
    """HTTP-level error returned by the API (4xx / 5xx)."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(f"API error {status}: {message}")


class OpenCodeGoContextWindowExceeded(OpenCodeGoError):
    """Model context limit reached — fatal, do not retry."""


class OpenCodeGoQuotaExceeded(OpenCodeGoError):
    """Quota exhausted — fatal, do not retry."""


class OpenCodeGoUsageNotIncluded(OpenCodeGoError):
    """Feature not included in the current subscription plan — fatal."""


class OpenCodeGoRateLimited(OpenCodeGoError):
    """Rate limited — retryable after *retry_after* seconds (if provided)."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(message)


class OpenCodeGoServerOverloaded(OpenCodeGoError):
    """Service temporarily unavailable — retryable."""


class OpenCodeGoStreamError(OpenCodeGoError):
    """Low-level streaming or SSE parsing error."""
