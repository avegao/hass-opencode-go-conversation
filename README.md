# OpenCode Go Conversation

A [Home Assistant](https://www.home-assistant.io/) custom integration that brings **OpenCode Go** models into your smart home as a conversation agent.

## Features

- API key setup flow for OpenCode Go
- Home Assistant Assist / conversation integration
- AI Task support for structured data generation
- Streaming responses
- Multi-turn conversations with chat history
- Model selector based on OpenCode Go models
- OpenCode Go-compatible client identification and conversation session headers
- HACS-compatible repository layout

## Requirements

| Requirement | Details |
| --- | --- |
| Home Assistant | 2026.3.0 or newer |
| Subscription | OpenCode Go |

## Installation

### HACS

1. Open HACS and go to **Integrations**.
2. Open the menu and choose **Custom repositories**.
3. Add this repository URL as an **Integration** repository.
4. Search for **OpenCode Go Conversation** and install it.
5. Restart Home Assistant.

### Manual

1. Copy `custom_components/opencode_go_conversation` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings -> Devices & Services -> Add Integration**.
2. Search for **OpenCode Go Conversation**.
3. Paste your OpenCode Go API key.

If you need to change the key later, open the integration menu and use **Reconfigure**.

## Notes

- This integration uses OpenCode Go's API-key authenticated API.
- Models are fetched from the OpenCode Go catalog and prefixed with `opencode-go/`.
- The client keeps the endpoint mapping in one registry: Responses models use
  `/responses`, OpenAI-compatible models use `/chat/completions`, and Anthropic
  models use `/messages`. The Home Assistant prefix is removed before sending
  the wire request.
- Catalog entries without a documented endpoint mapping are hidden until the
  registry is updated, preventing malformed requests when OpenCode adds a model.
- Generation requests identify this integration with an explicit user agent and send
  a stable `x-opencode-session` value derived from the Home Assistant conversation
  ID, as required by OpenCode Go.
- There is no background traffic or automatic retry loop; tool-call follow-up turns
  are bounded to 10 per interaction.
