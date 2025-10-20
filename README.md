# MCP Google Chat Server

This is a simple task message sender for Google Chat via webhook, designed to be used with the MCP (Modular Chat Platform) framework.

- Tool name: `task-messager`
- Env var required: `GOOGLE_CHAT_WEBHOOK_URL`
- Optional env var: `TASK_OWNER` (default task owner if not provided in message)

## Running locally

```bash
# inside this folder
uv sync
uv run task-messager.server
```

## Message schema

Input JSON:
- title: string
- description: string
- task_duration: string

Response JSON:
- success: bool
- message: string
- http_status: number (optional)

## Docker

Build image and run server:

```bash
docker build -t task-messager -f Dockerfile .
docker run --rm -e GOOGLE_CHAT_WEBHOOK_URL=*** -e TASK_OWNER="" -p 8080:8080 task-messager
```

## MCP client config example

Add in your MCP client config:

```json
{
  "mcpServers": {
    "task-messager": {
      "command": "python",
      "args": ["-m", "task-messager.server"],
      "env": {
        "GOOGLE_CHAT_WEBHOOK_URL": "https://chat.googleapis.com/v1/spaces/...",
        "TASK_OWNER": "A.."
      }
    }
  }
}
```
