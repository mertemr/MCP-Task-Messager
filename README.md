# MCP Google Chat Server

This is a Google Chat webhook server that posts structured Destek/Data görev kartları through the MCP (Modular Chat Platform) framework.

- Tool name: `task-messager`
- Env var required: `GOOGLE_CHAT_WEBHOOK_URL`
- Optional env vars: `TASK_OWNER`, `MCP_HOST`, `MCP_PORT`, `LOG_LEVEL`

## Quick Start

### 1. Set up environment variables

Copy the example file and configure your values:

```bash
cp .env.example .env
# Edit .env and set your GOOGLE_CHAT_WEBHOOK_URL
```

### 2. Running locally

```bash
# inside this folder
uv sync
uv run task-messager
```

## Message schema

Input JSON:

- `title`: string — card header (örn. `DATA/Destek (Analiz): ...`)
- `summary`: string — "Özet" bölümündeki kısa açıklama
- `problem`: string — bildirilen sorun/hipotez
- `estimated_duration`: string — tahmini süre (örn. `2 Saat`)
- `task_owner` (optional): string — görevin sorumlusu
- `analysis_steps` (optional): list of objects `{ "title": str, "detail": str }`
- `acceptance_criteria` (optional): list of strings

Response JSON:

- `success`: bool
- `message`: string
- `http_status`: number (optional)

Varsayılan "Muhtemel Çözüm" adımları ve "Kabul Kriterleri" uygulamanın içinde yerleşik olarak gelir; payload'da göndererek override edebilirsiniz.

## Docker

Build and run the server in a container:

```bash
# Build the image
docker build -t task-messager:latest .

# Run with environment variables
docker run --rm \
  -e GOOGLE_CHAT_WEBHOOK_URL="your-webhook-url" \
  -e TASK_OWNER="Default Owner" \
  -e LOG_LEVEL="INFO" \
  -p 8000:8000 \
  task-messager:latest
```

Or use an .env file:

```bash
docker run --rm --env-file .env -p 8000:8000 task-messager:latest
```

## MCP Client Configuration

### Windsurf / Claude Desktop / Cline

Add this configuration to your MCP settings file:
- Windsurf: `.windsurf/mcp.json`
- Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)
- Cline: VSCode settings

```json
{
  "mcpServers": {
    "task-messager": {
      "command": "uv",
      "args": [
        "--directory",
        "<PATH_TO_REPO>",
        "run",
        "task-messager"
      ],
      "env": {
        "GOOGLE_CHAT_WEBHOOK_URL": "<YOUR_GOOGLE_CHAT_WEBHOOK>",
        "TASK_OWNER": "<DEFAULT_TASK_OWNER>",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Alternative with Python directly:**

```json
{
  "mcpServers": {
    "task-messager": {
      "command": "python",
      "args": [
        "-m",
        "task_messager.server"
      ],
      "cwd": "<PATH_TO_REPO>",
      "env": {
        "GOOGLE_CHAT_WEBHOOK_URL": "<YOUR_GOOGLE_CHAT_WEBHOOK>",
        "TASK_OWNER": "<DEFAULT_TASK_OWNER>",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

> **Important:** Replace `<PATH_TO_REPO>` with the absolute path to this repository and `<YOUR_GOOGLE_CHAT_WEBHOOK>` with your actual webhook URL. Never commit credentials to version control.
