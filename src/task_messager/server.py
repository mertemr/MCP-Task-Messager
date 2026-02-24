import html
import os
import sys
from textwrap import dedent
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from task_messager import __version__
from task_messager.core import DOMAINS
from task_messager.logger import setup_logging
from task_messager.models import SendMessageInput, SendMessageResult, SolutionStep

try:
    import dotenv

    dotenv.load_dotenv()
except ImportError:
    pass

logger = setup_logging()
app = FastMCP(
    name="task-mcp",
    instructions=dedent("""
        You are a helpful assistant that formats support investigation tasks
        into structured messages and sends them to a Google Chat space via webhook.

        Available domains / task types:
          - backend   : API, database, queue, microservice issues
          - frontend  : UI bug, rendering, performance, browser compatibility
          - devops    : CI/CD, infrastructure, Docker, cloud, deployment
          - mobile    : iOS/Android crash, build, store submission
          - data      : Data pipeline, ETL, analytics, reporting issues
          - business  : Non-technical tasks like documentation, process improvement, etc.
          - general   : Catch-all when domain is unclear

        When the user describes a task, pick the most suitable domain so that
        domain-specific investigation steps and acceptance criteria are pre-filled.
        The user can override any field explicitly.

        Always confirm the filled-in card details before sending unless the user
        explicitly says "gönder" or "send directly".
    """),
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8000")),
)

httpx_client = httpx.AsyncClient(
    headers={"User-Agent": f"MCP-Task-Messager/{__version__}"},
    timeout=httpx.Timeout(15.0, connect=10.0),
)


def _format_summary_block(summary: str, problem: str) -> str:
    return f"<b>Özet:</b> {html.escape(summary)}<br><br><b>Problem:</b> {html.escape(problem)}"


def _format_analysis_steps(steps: list[SolutionStep]) -> str:
    lines = []
    for step in steps:
        lines.append(f"• <b>{html.escape(step.title)}:</b> {html.escape(step.detail)}")
    return "<br>".join(lines)


def _format_acceptance_criteria(criteria: list[str]) -> str:
    return "<br>".join(f"• {html.escape(item)}" for item in criteria)


# ---------------------------------------------------------------------------
# Card builder
# ---------------------------------------------------------------------------


def build_cards_payload(data: SendMessageInput) -> dict[str, Any]:
    """Build Google Chat cards payload that follows the investigation template."""

    domain_info = data.resolved_domain()
    domain_label = domain_info.get("label", "Genel")

    sections: list[dict[str, Any]] = []

    meta_widgets: list[dict[str, Any]] = [
        {
            "keyValue": {
                "topLabel": "Alan",
                "content": f"{html.escape(domain_label)}",
            }
        },
        {
            "keyValue": {
                "topLabel": "Tahmini Süre",
                "content": html.escape(data.estimated_duration),
            }
        },
    ]

    if data.task_owner:
        meta_widgets.append({
            "keyValue": {
                "topLabel": "Sorumlu",
                "content": html.escape(str(data.task_owner)),
            }
        })

    sections.append({"widgets": meta_widgets})

    sections.append({
        "header": "Görev Açıklaması",
        "widgets": [{"textParagraph": {"text": _format_summary_block(data.summary, data.problem)}}],
    })

    sections.append({
        "header": "Muhtemel Çözüm",
        "widgets": [{"textParagraph": {"text": _format_analysis_steps(data.resolved_steps())}}],
    })

    sections.append({
        "header": "Kabul Kriterleri",
        "widgets": [{"textParagraph": {"text": _format_acceptance_criteria(data.resolved_criteria())}}],
    })

    card = {
        "header": {"title": data.title},
        "sections": sections,
    }

    return {"cards": [card]}


# ---------------------------------------------------------------------------
# Webhook sender
# ---------------------------------------------------------------------------


async def post_to_webhook(payload: dict[str, Any]) -> SendMessageResult:
    url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL", "").strip()
    if not url:
        logger.warning("GOOGLE_CHAT_WEBHOOK_URL environment variable not set")
        return SendMessageResult(success=False, message="GOOGLE_CHAT_WEBHOOK_URL is not set")

    try:
        logger.info("Sending message to Google Chat webhook")
        resp = await httpx_client.post(url, json=payload)
        resp.raise_for_status()
        logger.info(f"Message sent successfully: HTTP {resp.status_code}")
        return SendMessageResult(success=True, message="Message sent", http_status=resp.status_code)
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


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@app.tool(
    title="Send Google Chat Message",
    description=(
        "Send a structured investigation task message to Google Chat space via webhook. "
        "Pick the correct domain so that investigation steps and acceptance criteria are "
        "automatically pre-filled: 'backend', 'frontend', 'devops', 'mobile', 'data', 'business', or 'general'."
    ),
)
async def send_google_chat_message(
    title: str,
    summary: str,
    problem: str,
    estimated_duration: str,
    domain: str = "general",
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
        domain: Task domain — backend | frontend | devops | mobile | data | business | general
        task_owner: Person responsible (optional, falls back to TASK_OWNER env var)
        analysis_steps: Custom investigation steps (optional, uses domain defaults if omitted)
        acceptance_criteria: Custom acceptance criteria (optional, uses domain defaults if omitted)
    """
    try:
        effective_task_owner = task_owner or os.getenv("TASK_OWNER")

        resolved_steps: list[SolutionStep] | None = None
        if analysis_steps is not None:
            resolved_steps = [SolutionStep(**step) for step in analysis_steps]

        data = SendMessageInput(
            title=title,
            summary=summary,
            problem=problem,
            estimated_duration=estimated_duration,
            domain=domain,
            task_owner=effective_task_owner,
            analysis_steps=resolved_steps,
            acceptance_criteria=acceptance_criteria,
        )
    except Exception as e:
        logger.error(f"Failed to parse input: {e}")
        return SendMessageResult(success=False, message=f"Invalid input: {e}").model_dump()

    payload = build_cards_payload(data)
    result = await post_to_webhook(payload)
    return result.model_dump()


@app.tool(
    title="List Available Domains",
    description=(
        "List all available task domains with their labels and default steps. Useful to understand what domain to pick."
    ),
)
async def list_domains() -> dict[str, Any]:
    """Return all available domains and their metadata."""
    return {
        domain_key: {
            "label": info["label"],
            "default_steps": [s["title"] for s in info["analysis_steps"]],
            "default_criteria_count": len(info["acceptance_criteria"]),
        }
        for domain_key, info in DOMAINS.items()
    }


def main() -> None:
    logger.info("Starting MCP server...")
    try:
        app.run(transport="sse")
    except KeyboardInterrupt:
        logger.info("Interrupted")
        sys.exit(0)
    except Exception as e:
        logger.exception("Server error occurred: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
