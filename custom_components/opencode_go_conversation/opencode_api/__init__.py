"""
opencode_api — Python client for the OpenCode Go Responses API.
"""

from __future__ import annotations

from .auth import AbstractAuth, OpenCodeGoAuth
from .client import MODELS_PATH, RESPONSES_PATH, OpenCodeGoClient
from .errors import (
    OpenCodeGoApiError,
    OpenCodeGoContextWindowExceeded,
    OpenCodeGoError,
    OpenCodeGoQuotaExceeded,
    OpenCodeGoRateLimited,
    OpenCodeGoServerOverloaded,
    OpenCodeGoStreamError,
    OpenCodeGoUsageNotIncluded,
)
from .models import (
    FunctionCallAdded,
    FunctionCallArgumentsDelta,
    FunctionCallArgumentsDone,
    OutputItemAdded,
    OutputItemDone,
    OutputTextDelta,
    RateLimits,
    ReasoningContentDelta,
    ReasoningSummaryDelta,
    ResponseCompleted,
    ResponseCreated,
    ResponseEvent,
)
from .requests import OpenCodeGoRequest

__all__ = [
    "AbstractAuth",
    "OpenCodeGoAuth",
    "MODELS_PATH",
    "RESPONSES_PATH",
    "OpenCodeGoClient",
    "OpenCodeGoError",
    "OpenCodeGoApiError",
    "OpenCodeGoContextWindowExceeded",
    "OpenCodeGoQuotaExceeded",
    "OpenCodeGoUsageNotIncluded",
    "OpenCodeGoRateLimited",
    "OpenCodeGoServerOverloaded",
    "OpenCodeGoStreamError",
    "ResponseCreated",
    "OutputItemAdded",
    "OutputTextDelta",
    "ReasoningContentDelta",
    "ReasoningSummaryDelta",
    "OutputItemDone",
    "ResponseCompleted",
    "RateLimits",
    "FunctionCallAdded",
    "FunctionCallArgumentsDelta",
    "FunctionCallArgumentsDone",
    "ResponseEvent",
    "OpenCodeGoRequest",
]
