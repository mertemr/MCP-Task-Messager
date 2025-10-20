from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

import httpx
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field


class SendMessageInput(BaseModel):
    title: str = Field(..., description="Card header title")
    description: str = Field(..., description="Short paragraph for the card body")
    task_duration: Optional[str] = Field(None, description="Görev süresi, ör: '2 saat' veya 'PT30M'")
    task_owner: Optional[str] = Field(None, description="Görevin sorumlusu")


class SendMessageResult(BaseModel):
    success: bool
    message: str
    http_status: Optional[int] = None


def build_cards_payload(data: SendMessageInput) -> Dict[str, Any]:
    """Build simple cards payload for Google Chat webhook."""
    task_owner = os.getenv("TASK_OWNER", "").strip()
    if task_owner and not data.task_owner:
        data.task_owner = task_owner

    widgets: list[dict[str, Any]] = []

    if data.description:
        widgets.append({"textParagraph": {"text": str(data.description)}})

    if data.task_duration:
        widgets.append({"keyValue": {"topLabel": "Süre", "content": str(data.task_duration)}})
    
    if data.task_owner:
        widgets.append({"keyValue": {"topLabel": "Sorumlu", "content": str(data.task_owner)}})

    card = {
        "header": {
            "title": str(data.title),
        },
        "sections": [
            {"widgets": widgets} if widgets else {"widgets": [{"textParagraph": {"text": str(data.description)}}]}
        ],
    }

    payload: Dict[str, Any] = {"cards": [card]}
    return payload


async def post_to_webhook(payload: Dict[str, Any]) -> SendMessageResult:
    url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL", "").strip()
    if not url:
        return SendMessageResult(success=False, message="GOOGLE_CHAT_WEBHOOK_URL is not set")

    timeout = httpx.Timeout(10.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload)
            if 200 <= resp.status_code < 300:
                return SendMessageResult(success=True, message="Message sent", http_status=resp.status_code)

            return SendMessageResult(
                success=False,
                message=f"HTTP {resp.status_code}: {resp.text}",
                http_status=resp.status_code,
            )
        except httpx.RequestError as e:
            return SendMessageResult(success=False, message=f"Request error: {e}")


app = FastMCP("google-chat")


@app.tool()
async def send_google_chat_message(ctx: Context, **kwargs) -> dict[str, Any]:
    """Send a task message to Google Chat via webhook. 

    Required fields:
    - title: Task title
    - description: task description
    - task_duration: Task duration (e.g., '2 hours')
    
    """
    try:
        if "kwargs" in kwargs:
            wrapped = kwargs.get("kwargs")
            if isinstance(wrapped, str):
                try:
                    kwargs = json.loads(wrapped)
                except Exception:
                    pass
            elif isinstance(wrapped, dict):
                kwargs = wrapped

        for container_key in ("data", "input", "payload"):
            if container_key in kwargs and isinstance(kwargs[container_key], dict):
                kwargs = kwargs[container_key]
                break

        data = SendMessageInput(**kwargs)
    except Exception as e:
        return SendMessageResult(success=False, message=f"Invalid input: {e}").model_dump()

    payload = build_cards_payload(data)
    result = await post_to_webhook(payload)
    return result.model_dump()


def main() -> None:
    try:
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
