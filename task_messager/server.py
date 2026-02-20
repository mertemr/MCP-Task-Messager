from __future__ import annotations

import html
import json
import os
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field


def _default_analysis_steps() -> list[dict[str, str]]:
    """Return the default investigation checklist for the card."""

    return [
        {
            "title": "Sorgulama",
            "detail": (
                "İletilen fatura ID/numaraları kullanılarak header ve lines tablolarındaki tutar uyumu kontrol edilir."
            ),
        },
        {
            "title": "Log Analizi",
            "detail": ("LOG tablolarından oluşturma, güncelleme ve statü değişiklikleri incelenir."),
        },
        {
            "title": "Entegrasyon Kontrolü",
            "detail": ("Transfer kuyruğunda (queue) bekleyen kayıtlar ve hata mesajları gözden geçirilir."),
        },
        {
            "title": "Bulgu Paylaşımı",
            "detail": ("Tespit edilen anomali veya çözüm önerisi teknik dille raporlanır."),
        },
    ]


def _default_acceptance_criteria() -> list[str]:
    """Return default acceptance checklist entries."""

    return [
        "Şüpheli faturaların ham verisi incelenmiş ve dökümü alınmıştır.",
        ("Sorunun kaynağı (kullanıcı hatası mı yoksa yazılım bug'ı mı) netleştirilmiştir."),
        ("Analiz sonucu ve çözüm önerisi talep sahibine iletilmiştir."),
    ]


class SolutionStep(BaseModel):
    """Describe a single investigation step within the solution plan."""

    title: str = Field(..., description="Step heading, e.g., 'Sorgulama'")
    detail: str = Field(..., description="Step explanation")


class SendMessageInput(BaseModel):
    """Structured data model representing a support investigation task."""

    title: str = Field(..., description="Task title, shown in the card header")
    summary: str = Field(..., description="High level summary of the task")
    problem: str = Field(..., description="Problem statement")
    estimated_duration: str = Field(..., description="Estimated effort, e.g. '2 Saat'")
    task_owner: str | None = Field(None, description="Görevin sorumlusu")
    analysis_steps: list[SolutionStep] = Field(
        default_factory=_default_analysis_steps,
        description="Ordered checklist under 'Muhtemel Çözüm'",
    )
    acceptance_criteria: list[str] = Field(
        default_factory=_default_acceptance_criteria,
        description="Items listed under 'Kabul Kriterleri'",
    )


class SendMessageResult(BaseModel):
    """Represent the response returned to the MCP client."""

    success: bool
    message: str
    http_status: int | None = None


def _format_summary_block(summary: str, problem: str) -> str:
    """Return HTML block containing summary and problem statements."""

    return (
        f"<b>Özet:</b> {html.escape(summary)}<br><br>"
        f"<b>Problem:</b> {html.escape(problem)}"
    )  # fmt: skip


def _format_analysis_steps(steps: list[Any]) -> str:
    """Return a HTML bullet list describing the investigation plan."""

    lines = []
    for step in steps:
        if isinstance(step, SolutionStep):
            title = step.title
            detail = step.detail
        elif isinstance(step, dict):
            title = str(step.get("title", "Adım"))
            detail = str(step.get("detail", ""))
        else:
            title = str(step)
            detail = ""

        lines.append("• " + f"<b>{html.escape(title)}:</b> " + html.escape(detail))
    return "<br>".join(lines)


def _format_acceptance_criteria(criteria: list[str]) -> str:
    """Return acceptance criteria as an HTML bullet list."""

    return "<br>".join(f"• {html.escape(item)}" for item in criteria)


def build_cards_payload(data: SendMessageInput) -> dict[str, Any]:
    """Build Google Chat cards payload that follows the investigation template."""

    # Sorumlu alanı her zaman tek bir kişiyle paylaşılacak.
    data.task_owner = "Gökhan Elbistan"

    sections: list[dict[str, Any]] = []
    meta_widgets: list[dict[str, Any]] = []

    meta_widgets.append({
        "keyValue": {
            "topLabel": "Tahmini Süre",
            "content": html.escape(data.estimated_duration),
        }
    })

    if data.task_owner:
        meta_widgets.append({
            "keyValue": {
                "topLabel": "Sorumlu",
                "content": html.escape(str(data.task_owner)),
            }
        })

    if meta_widgets:
        sections.append({"widgets": meta_widgets})

    sections.append({
        "header": "Görev Açıklaması",
        "widgets": [{"textParagraph": {"text": _format_summary_block(data.summary, data.problem)}}],
    })

    sections.append({
        "header": "Muhtemel Çözüm",
        "widgets": [{"textParagraph": {"text": _format_analysis_steps(data.analysis_steps)}}],
    })

    sections.append({
        "header": "Kabul Kriterleri",
        "widgets": [{"textParagraph": {"text": _format_acceptance_criteria(data.acceptance_criteria)}}],
    })

    card = {"header": {"title": str(data.title)}, "sections": sections}

    payload: dict[str, Any] = {"cards": [card]}
    return payload


async def post_to_webhook(payload: dict[str, Any]) -> SendMessageResult:
    """Send the prepared payload to Google Chat webhook and wrap the response."""

    url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL", "").strip()
    if not url:
        return SendMessageResult(success=False, message="GOOGLE_CHAT_WEBHOOK_URL is not set")

    timeout = httpx.Timeout(10.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload)
            if 200 <= resp.status_code < 300:
                return SendMessageResult(
                    success=True,
                    message="Message sent",
                    http_status=resp.status_code,
                )

            return SendMessageResult(
                success=False,
                message=f"HTTP {resp.status_code}: {resp.text}",
                http_status=resp.status_code,
            )
        except httpx.RequestError as exc:
            return SendMessageResult(success=False, message=f"Request error: {exc}")


app = FastMCP("google-chat")


@app.tool()
async def send_google_chat_message(ctx: Context, **kwargs) -> dict[str, Any]:
    """Send a structured investigation task message to Google Chat."""
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
    """Entrypoint that starts the FastMCP server."""

    try:
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
