import html
import logging
import os
import sys
from textwrap import dedent
from typing import Any

import dotenv
import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

dotenv.load_dotenv()


def _setup_logging() -> logging.Logger:
    """Configure and return the module logger."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger = logging.getLogger("task_messager")
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.addHandler(handler)
    logger.propagate = False

    return logger


logger = _setup_logging()
app = FastMCP(
    name="google-chat",
    instructions=dedent("""
        You are a helpful assistant that formats support investigation tasks
        into structured messages and sends them toa Google Chat space via webhook.
        The messages should follow a specific template with sections for task description,
        investigation steps, and acceptance criteria.
    """),
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_PORT", "8000")),
)
httpx_client = httpx.AsyncClient(
    headers={"User-Agent": "MCP-Task-Messager/1.0"},
    timeout=httpx.Timeout(15.0, connect=10.0),
)


# ---------------------------------------------------------------------------
# Default values for SendMessageInput fields
# ---------------------------------------------------------------------------
DEFAULT_ANALYSIS_STEPS: list[dict[str, str]] = [
    {
        "title": "Sorgulama",
        "detail": "İletilen fatura ID/numaraları kullanılarak header ve lines tablolarındaki tutar uyumu kontrol edilir.",  # noqa: E501
    },
    {
        "title": "Log Analizi",
        "detail": "LOG tablolarından oluşturma, güncelleme ve statü değişiklikleri incelenir.",
    },
    {
        "title": "Entegrasyon Kontrolü",
        "detail": "Transfer kuyruğunda (queue) bekleyen kayıtlar ve hata mesajları gözden geçirilir.",
    },
    {
        "title": "Bulgu Paylaşımı",
        "detail": "Tespit edilen anomali veya çözüm önerisi teknik dille raporlanır.",
    },
]

DEFAULT_ACCEPTANCE_CRITERIA: list[str] = [
    "Şüpheli faturaların ham verisi incelenmiş ve dökümü alınmıştır.",
    "Sorunun kaynağı (kullanıcı hatası mı yoksa yazılım bug'ı mı) netleştirilmiştir.",
    "Analiz sonucu ve çözüm önerisi talep sahibine iletilmiştir.",
]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
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
        default_factory=lambda: [SolutionStep.model_validate(step) for step in DEFAULT_ANALYSIS_STEPS],
        description="Ordered checklist under 'Muhtemel Çözüm'",
    )
    acceptance_criteria: list[str] = Field(
        default_factory=lambda: list(DEFAULT_ACCEPTANCE_CRITERIA),
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
        logger.warning("GOOGLE_CHAT_WEBHOOK_URL environment variable not set")
        return SendMessageResult(success=False, message="GOOGLE_CHAT_WEBHOOK_URL is not set")

    try:
        logger.info("Sending message to Google Chat webhook")
        resp = await httpx_client.post(url, json=payload)
        resp.raise_for_status()

        logger.info(f"Message sent successfully: HTTP {resp.status_code}")
        return SendMessageResult(
            success=True,
            message="Message sent",
            http_status=resp.status_code,
        )
    except httpx.HTTPStatusError:
        logger.error(f"Failed to send message: HTTP {resp.status_code} - {resp.text}")
        return SendMessageResult(
            success=False,
            message=f"HTTP {resp.status_code}: {resp.text}",
            http_status=resp.status_code,
        )
    except httpx.RequestError as exc:
        logger.exception(f"Request error while sending message: {exc}")
        return SendMessageResult(success=False, message=f"Request error: {exc}")


@app.tool(
    title="Send Google Chat Message",
    description="Send a structured investigation task message to Google Chat space via webhook",
)
async def send_google_chat_message(
    title: str,
    summary: str,
    problem: str,
    estimated_duration: str,
    task_owner: str | None = None,
    analysis_steps: list[dict[str, str]] | None = None,
    acceptance_criteria: list[str] | None = None,
) -> dict[str, Any]:
    """Send a structured investigation task message to Google Chat.

    Args:
        title: Task title shown in the card header
        summary: High level summary of the task
        problem: Detailed problem statement
        estimated_duration: Estimated effort (e.g., '2 Saat')
        task_owner: Person responsible for the task (optional, falls back to TASK_OWNER env variable if not provided)
        analysis_steps: Custom investigation steps (optional, uses defaults if not provided)
        acceptance_criteria: Custom acceptance criteria (optional, uses defaults if not provided)
    """
    try:
        effective_task_owner = task_owner or os.getenv("TASK_OWNER")

        # Prepare the input data, using defaults where not provided
        input_data: dict[str, Any] = {
            "title": title,
            "summary": summary,
            "problem": problem,
            "estimated_duration": estimated_duration,
            "task_owner": effective_task_owner,
        }

        if analysis_steps is not None:
            input_data["analysis_steps"] = [SolutionStep(**step) for step in analysis_steps]

        if acceptance_criteria is not None:
            input_data["acceptance_criteria"] = acceptance_criteria

        data = SendMessageInput(**input_data)
    except Exception as e:
        logger.error(f"Failed to parse input: {e}")
        return SendMessageResult(success=False, message=f"Invalid input: {e}").model_dump()

    payload = build_cards_payload(data)
    result = await post_to_webhook(payload)
    return result.model_dump()


def main() -> None:
    """Entrypoint that starts the FastMCP server."""
    logger.info("Starting MCP server...")

    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted")
        sys.exit(0)
    except Exception as e:
        logger.exception("Server error occurred: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
