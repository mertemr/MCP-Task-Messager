import os
import sys
from typing import Any

import httpx

from task_messager.core import DOMAINS, app, httpx_client
from task_messager.formatter import build_cards_payload
from task_messager.logger import setup_logging
from task_messager.models import SendMessageInput, SendMessageResult, SolutionStep

try:
    import dotenv

    dotenv.load_dotenv()
except ImportError:
    pass

logger = setup_logging()


def _resolve_task_owner_and_participants(
    raw_owner: str | None, participants: list[str]
) -> tuple[str | None, list[str] | None]:
    effective_task_owner = None
    effective_participants: list[str] | None = None

    if isinstance(raw_owner, str) and "," in raw_owner and not participants:
        parts = [p.strip() for p in raw_owner.split(",") if p.strip()]
        if parts:
            effective_task_owner = parts[0]
            if len(parts) > 1:
                effective_participants = list(parts[1:])
    else:
        effective_task_owner = raw_owner
        effective_participants = participants

    if effective_participants is None:
        effective_participants = []

    effective_participants = [p.strip() for p in effective_participants if isinstance(p, str) and p.strip()]
    if effective_task_owner and isinstance(effective_task_owner, str):
        effective_participants = [p for p in effective_participants if p != effective_task_owner]

    return effective_task_owner, effective_participants


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
        "automatically pre-filled: 'backend', 'frontend', 'devops', 'mobile', 'data', 'business', or 'general'. "
        "IMPORTANT: task_owner is the single assignee of the task. "
        "participants are additional people to be notified — they are never the assignee. "
        "If the user says 'bana aç' or does not specify an assignee, use the TASK_OWNER env var. "
        "If the user says 'Ali'ye aç', set task_owner to Ali regardless of who else is mentioned."
    ),
)
async def send_google_chat_message(
    title: str,
    summary: str,
    problem: str,
    estimated_duration: str,
    domain: str = "general",
    task_owner: str | None = None,
    participants: list[str] | None = None,
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
        task_owner: The single person the task is ASSIGNED TO. Falls back to TASK_OWNER env var.
                    If the user says "Ali'ye aç", this should be "Ali".
                    If the user says "bana aç" or doesn't specify, use the env var default.
        participants: Additional observers/stakeholders. Shown as "Katılımcılar" in the card.
                      NEVER put participants in task_owner. These are informational only.
        analysis_steps: Custom investigation steps (optional, uses domain defaults if omitted)
        acceptance_criteria: Custom acceptance criteria (optional, uses domain defaults if omitted)
    """
    try:
        raw_owner = task_owner or os.getenv("TASK_OWNER")
        effective_task_owner, effective_participants = _resolve_task_owner_and_participants(raw_owner, participants)
        resolved_steps: list[SolutionStep] | None = None

        if analysis_steps is not None:
            resolved_steps = [SolutionStep.model_validate(step) for step in analysis_steps]
        elif domain in DOMAINS:
            resolved_steps = [SolutionStep.model_validate(step) for step in DOMAINS[domain]["analysis_steps"]]

        data = SendMessageInput(
            title=title,
            summary=summary,
            problem=problem,
            estimated_duration=estimated_duration,
            domain=domain,
            task_owner=effective_task_owner,
            participants=effective_participants or None,
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


@app.tool(
    title="List Members for name resolution",
    description=(
        "List all members that can be used for task_owner and participants."
        "Useful to understand how to specify assignees and participants."
    ),
)
async def list_members() -> dict[str, Any]:
    """Return a list of members for name resolution."""

    team_members = os.getenv("TEAM_MEMBERS", "")
    members = [m.strip() for m in team_members.split(",") if m.strip()]
    return {"members": members}


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
