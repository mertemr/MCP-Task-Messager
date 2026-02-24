from typing import Any, TypedDict

from pydantic import BaseModel, Field, field_validator

from task_messager.core import DOMAINS


class AnalysisStep(TypedDict):
    """Define a single step in the investigation checklist, with a title and detailed explanation."""

    title: str
    detail: str


class Domain(TypedDict):
    """Define investigation template for a specific domain, including checklist steps and acceptance criteria."""

    label: str
    analysis_steps: list[AnalysisStep]
    acceptance_criteria: list[str]


class SolutionStep(BaseModel):
    """Describe a single investigation step within the solution plan."""

    title: str = Field(..., description="Step heading, e.g., 'Sorgulama'")
    detail: str = Field(..., description="Step explanation")

    @field_validator("title", "detail")
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Must not be empty")
        return v.strip()


class SendMessageInput(BaseModel):
    """Structured data model representing a support investigation task."""

    title: str = Field(..., description="Task title, shown in the card header")
    summary: str = Field(..., description="High level summary of the task")
    problem: str = Field(..., description="Problem statement")
    estimated_duration: str = Field(..., description="Estimated effort, e.g. '2 Saat'")
    domain: str = Field(default="general", description="Task domain: backend | frontend | devops | mobile | general")
    task_owner: str | None = Field(None, description="Görevin sorumlusu")
    analysis_steps: list[SolutionStep] | None = Field(
        default=None,
        description="Ordered checklist under 'Muhtemel Çözüm'. Uses domain defaults when None.",
    )
    acceptance_criteria: list[str] | None = Field(
        default=None,
        description="Items listed under 'Kabul Kriterleri'. Uses domain defaults when None.",
    )

    @field_validator("domain")
    def validate_domain(cls, v: str) -> str:
        if v not in DOMAINS:
            raise ValueError(f"Invalid domain '{v}'. Must be one of: {', '.join(DOMAINS.keys())}")
        return v

    def resolved_domain(self) -> dict[str, Any]:
        return DOMAINS.get(self.domain, DOMAINS["general"])

    def resolved_steps(self) -> list[SolutionStep]:
        if self.analysis_steps:
            return self.analysis_steps
        return [SolutionStep.model_validate(s) for s in self.resolved_domain()["analysis_steps"]]

    def resolved_criteria(self) -> list[str]:
        if self.acceptance_criteria:
            return self.acceptance_criteria
        return list(self.resolved_domain()["acceptance_criteria"])


class SendMessageResult(BaseModel):
    """Represent the response returned to the MCP client."""

    success: bool
    message: str
    http_status: int | None = None

    @field_validator("message")
    def non_empty_message(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message must not be empty")
        return v.strip()
