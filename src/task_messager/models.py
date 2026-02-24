from typing import Any, TypedDict

from pydantic import BaseModel, Field, field_validator, model_validator

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
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Must not be empty")
        return v.strip()


class SendMessageInput(BaseModel):
    """Structured data model representing a support investigation task."""

    title: str = Field(..., description="Görevin kısa başlığı, tek cümle ile özet")
    summary: str = Field(..., description="Görevin detaylı açıklaması, bağlam ve önemli noktalar")
    problem: str = Field(..., description="Çözülmesi gereken spesifik problem veya soru")
    estimated_duration: str = Field(..., description="Görevin tamamlanması için tahmini süre, örn. '2 saat', '12 saat'")
    domain: str = Field(
        default="general", description=f"Task domain — one of: {', '.join(DOMAINS.keys())}, Varsayılan 'general'"
    )
    task_owner: str | None = Field(None, description="Görevin atandığı tek kişi")
    participants: list[str] | None = Field(
        default=None,
        description="Ek katılımcılar — task_owner ile karıştırılmamalı",
    )
    analysis_steps: list[SolutionStep] | None = Field(
        default=None,
        description="Görev için özel analiz adımları. Sağlanmazsa domain'e göre varsayılan adımlar kullanılır.",
    )
    acceptance_criteria: list[str] | None = Field(
        default=None,
        description="Görev kabul kriterleri. Sağlanmazsa domain'e göre varsayılan kriterler kullanılır.",
    )

    @field_validator("title", "summary", "problem", "estimated_duration")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Must not be empty")
        return v.strip()

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if v not in DOMAINS:
            raise ValueError(f"Invalid domain '{v}'. Must be one of: {', '.join(DOMAINS.keys())}")
        return v

    @field_validator("task_owner", mode="before")
    @classmethod
    def normalize_task_owner(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            first = v.split(",")[0].strip()
            return first.title() if first else None
        raise ValueError("task_owner must be a string")

    @field_validator("participants", mode="before")
    @classmethod
    def normalize_participants(cls, v: Any) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, str):
            parts = [p.strip().title() for p in v.split(",") if p.strip()]
            return parts or None
        if isinstance(v, list):
            cleaned = [item.strip() for item in v if isinstance(item, str) and item.strip()]
            return cleaned or None
        raise ValueError("participants must be a string or list of strings")

    @model_validator(mode="after")
    def ensure_no_task_owner_in_participants(self) -> "SendMessageInput":
        if self.task_owner and self.participants:
            self.participants = [p for p in self.participants if p != self.task_owner]
            if not self.participants:
                self.participants = None
        return self

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
    @classmethod
    def non_empty_message(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message must not be empty")
        return v.strip()
