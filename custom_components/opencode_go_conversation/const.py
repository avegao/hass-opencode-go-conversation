"""Constants for the OpenCode Go Conversation integration."""

from homeassistant.const import CONF_LLM_HASS_API  # noqa: F401
from homeassistant.helpers import llm

DOMAIN = "opencode_go_conversation"

MODEL_IDS = [
    "grok-4.5",
    "glm-5.2",
    "glm-5.1",
    "kimi-k3",
    "kimi-k2.7-code",
    "kimi-k2.6",
    "mimo-v2.5",
    "mimo-v2.5-pro",
    "minimax-m3",
    "minimax-m2.7",
    "minimax-m2.5",
    "qwen3.7-max",
    "qwen3.7-plus",
    "qwen3.6-plus",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "hy3",
]

MODELS = [f"opencode-go/{model_id}" for model_id in MODEL_IDS]

# Options keys
CONF_MODEL = "model"
CONF_RECOMMENDED = "recommended"
CONF_PROMPT = "prompt"
CONF_REASONING_EFFORT = "reasoning_effort"
CONF_REASONING_SUMMARY = "reasoning_summary"
CONF_TEXT_VERBOSITY = "text_verbosity"
CONF_API_KEY = "api_key"

# Defaults
DEFAULT_MODEL = "opencode-go/deepseek-v4-flash"
RECOMMENDED_REASONING_EFFORT = "medium"
RECOMMENDED_REASONING_SUMMARY = "off"
RECOMMENDED_TEXT_VERBOSITY = "medium"

RECOMMENDED_CONVERSATION_OPTIONS: dict = {
    CONF_RECOMMENDED: True,
    CONF_LLM_HASS_API: [llm.LLM_API_ASSIST],
    CONF_PROMPT: llm.DEFAULT_INSTRUCTIONS_PROMPT,
    CONF_MODEL: DEFAULT_MODEL,
    CONF_REASONING_EFFORT: RECOMMENDED_REASONING_EFFORT,
    CONF_REASONING_SUMMARY: RECOMMENDED_REASONING_SUMMARY,
    CONF_TEXT_VERBOSITY: RECOMMENDED_TEXT_VERBOSITY,
}

RECOMMENDED_AI_TASK_OPTIONS: dict = {
    CONF_RECOMMENDED: True,
    CONF_MODEL: DEFAULT_MODEL,
    CONF_REASONING_EFFORT: RECOMMENDED_REASONING_EFFORT,
    CONF_REASONING_SUMMARY: RECOMMENDED_REASONING_SUMMARY,
    CONF_TEXT_VERBOSITY: RECOMMENDED_TEXT_VERBOSITY,
}
