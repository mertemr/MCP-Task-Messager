# task-messager

Google Chat webhook sunucusu; MCP (Modular Chat Platform) üzerinden yapılandırılmış görev kartları gönderir.

## İçindekiler

- [Hızlı Başlangıç](#hızlı-başlangıç)
- [Çalıştırma (Docker ve Lokal)](#çalıştırma-docker-ve-lokal)
- [MCP İstemci Konfigürasyonu](#mcp-istemci-konfigürasyonu)
- [Çevresel Değişkenler](#çevresel-değişkenler)
- [Mesaj Şeması](#mesaj-şeması)

## Hızlı Başlangıç

1. Ortam değişkenlerini ayarlayın (örnek `.env.example`):

```bash
cp .env.example .env
# .env içinde GOOGLE_CHAT_WEBHOOK_URL değerini ayarlayın
```

2. Lokal geliştirme:

```bash
# repository kökünden
uv sync
uv run task-messager
```

## Çalıştırma (Docker ve Lokal)

Docker ile çalıştırma:

```bash
docker build -t task-messager:latest .
docker run --rm -e GOOGLE_CHAT_WEBHOOK_URL="your-webhook-url" -e TASK_OWNER="Default Owner" -e LOG_LEVEL="INFO" -p 8000:8000 task-messager:latest
```

`.env` dosyasıyla:

```bash
docker run --rm --env-file .env -p 8000:8000 task-messager:latest
```

## MCP İstemci Konfigürasyonu

Aşağıda popüler MCP istemcileri için örnek konfigürasyonlar yer alır. `PATH_TO_REPO` ve `YOUR_GOOGLE_CHAT_WEBHOOK` değerlerini kendi ortamınıza göre değiştirin.

- VSCode (`.vscode/mcp.json`)

```json
{
  "servers": {
    "task-mcp": {
      "type": "sse",
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

- Windsurf (`.windsurf/mcp.json`)

```json
{
  "mcpServers": {
    "task-messager": {
      "command": "uv",
      "args": ["--directory", "<PATH_TO_REPO>", "run", "task-messager"],
      "env": {
        "GOOGLE_CHAT_WEBHOOK_URL": "<YOUR_GOOGLE_CHAT_WEBHOOK>",
        "TASK_OWNER": "<DEFAULT_TASK_OWNER>",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

- Claude Desktop (macOS / Windows)

Dosya konumları:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\\Claude\\claude_desktop_config.json`

İçerik örneği (JSON içinde `mcpServers` alanına ekleyin):

```json
{
  "mcpServers": {
    "task-messager": {
      "command": "uv",
      "args": ["--directory", "<PATH_TO_REPO>", "run", "task-messager"],
      "env": { "GOOGLE_CHAT_WEBHOOK_URL": "<YOUR_GOOGLE_CHAT_WEBHOOK>" }
    }
  }
}
```

- Cline (VSCode settings veya Cline konfigürasyonu)

VSCode ayarlarına eklemek için örnek:

```json
"mcpServers": {
  "task-messager": {
    "command": "uv",
    "args": ["--directory", "<PATH_TO_REPO>", "run", "task-messager"],
    "env": {"GOOGLE_CHAT_WEBHOOK_URL": "<YOUR_GOOGLE_CHAT_WEBHOOK>"}
  }
}
```

- Alternatif (Python doğrudan)

```json
{
  "mcpServers": {
    "task-messager": {
      "command": "python",
      "args": ["-m", "task_messager.server"],
      "cwd": "<PATH_TO_REPO>",
      "env": { "GOOGLE_CHAT_WEBHOOK_URL": "<YOUR_GOOGLE_CHAT_WEBHOOK>" }
    }
  }
}
```

## Çevresel Değişkenler

- `GOOGLE_CHAT_WEBHOOK_URL` (zorunlu): Google Chat Incoming Webhook URL
- `TASK_OWNER` (opsiyonel): Görev için varsayılan sorumlu
- `MCP_HOST`, `MCP_PORT` (opsiyonel): MCP ile ilgili ayarlar
- `LOG_LEVEL` (opsiyonel): `INFO`, `DEBUG`, vb.

## Mesaj Şeması

Input JSON alanları (kısa):

- `title`: string — kart başlığı
- `summary`: string — kısa özet
- `problem`: string — bildirilen sorun veya hipotez
- `estimated_duration`: string — tahmini süre (örn. `2 Saat`)
- `task_owner` (opsiyonel): string
- `analysis_steps` (opsiyonel): liste `{ "title": str, "detail": str }`
- `acceptance_criteria` (opsiyonel): liste string

Response JSON:

- `success`: bool
- `message`: string
- `http_status`: number (opsiyonel)
