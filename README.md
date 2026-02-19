# MCP Google Chat Server

This is a Google Chat webhook server that posts structured Destek/Data görev kartları through the MCP (Modular Chat Platform) framework.

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

Build image and run server:

```bash
docker build -t task-messager -f Dockerfile .
docker run --rm -e GOOGLE_CHAT_WEBHOOK_URL=*** -e TASK_OWNER="" -p 8080:8080 task-messager
```

## Windsurf MCP client config

`.windsurf/mcp.json` dosyanıza aşağıdaki girdiyi ekleyin:

```json
{
  "mcpServers": {
    "task-messager": {
      "command": "python",
      "args": [
        "<PATH_TO_PYTHON_EXE>",
        "<PATH_TO_REPO>/task_messager/server.py"
      ],
      "env": {
        "GOOGLE_CHAT_WEBHOOK_URL": "<YOUR_GOOGLE_CHAT_WEBHOOK>",
        "TASK_OWNER": "<DEFAULT_TASK_OWNER>"
      }
    }
  }
}
```

> Not: `PATH_TO_PYTHON_EXE`, depo yolu ve webhook URL’sini kendi ortamınıza göre doldurun; bu değerleri repoya koymayın.
