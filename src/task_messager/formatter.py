import html
import re
from typing import Any

from task_messager.models import SendMessageInput, SolutionStep, SolutionStepSection, TaskDescription

type Payload = dict[str, Any]

DOMAIN_PREFIX: dict[str, str] = {
    "backend": "Backend",
    "frontend": "Frontend",
    "devops": "DevOps",
    "mobile": "Mobil",
    "data": "Data",
    "business": "Business",
    "general": "",
}

_VALID_SUFFIXES = (
    "Edilecek",
    "Yapılacak",
    "Geliştirilecek",
    "Düzenlenecek",
    "İncelenecek",
    "Araştırılacak",
    "Oluşturulacak",
    "Kaldırılacak",
    "Güncellenecek",
    "Entegre Edilecek",
    "Test Edilecek",
    "Analiz Edilecek",
)


def format_title(raw_title: str, project: str, domain: str) -> str:
    """Normalize task title into a consistent format: `[Project] [DomainPrefix]: [Action]`"""

    action = raw_title.strip()

    # Remove trailing punctuation and whitespace
    action = action.rstrip(".!?;: ")

    # Case-insensitive check for already-correct future-tense suffixes
    action_lower = action.lower()
    valid_suffixes_lower = tuple(s.lower() for s in _VALID_SUFFIXES)
    if not any(action_lower.endswith(suffix) for suffix in valid_suffixes_lower):
        action = _nominalize_to_future(action)

    domain_prefix = DOMAIN_PREFIX.get(domain, "")
    parts = [p for p in [project.strip(), domain_prefix] if p]
    prefix = " ".join(parts)

    if prefix:
        return f"{prefix}: {action}"
    return action


def _nominalize_to_future(action: str) -> str:
    """Nominalize action verbs to future tense if they end with a common verb root"""

    replacements = [
        (r"Geliştirme$", "Geliştirilecek"),
        (r"Düzenleme$", "Düzenlenecek"),
        (r"İnceleme$", "İncelenecek"),
        (r"Araştırma$", "Araştırılacak"),
        (r"Oluşturma$", "Oluşturulacak"),
        (r"Kaldırma$", "Kaldırılacak"),
        (r"Güncelleme$", "Güncellenecek"),
        (r"Test Etme$", "Test Edilecek"),
        (r"Entegrasyon$", "Entegre Edilecek"),
        (r"Analiz$", "Analiz Edilecek"),
        (r"Düzeltme$", "Düzeltilecek"),
    ]
    for pattern, replacement in replacements:
        if re.search(pattern, action, re.IGNORECASE):
            return re.sub(pattern, replacement, action, flags=re.IGNORECASE)

    return f"{action} Yapılacak"


def to_markdown(title: str, desc: TaskDescription) -> str:
    """Görev açıklamasını Markdown formatında döner.

    Scrum master template'ini tam olarak uygular::

        **Özet:** ...
        **Problem:** ...
        **Muhtemel Çözüm:**
        1. **Adım Başlığı:**
           - Madde
        **Çözümün Avantajları:**
        - Avantaj 1
    """
    lines: list[str] = [f"# {title}", ""]

    lines.append(f"**Özet:** {desc.summary}")
    lines.append("")
    lines.append(f"**Problem:** {desc.problem}")
    lines.append("")

    lines.append("**Muhtemel Çözüm:**")
    for i, step in enumerate(desc.solution_steps, start=1):
        lines.append(f"{i}. **{step.title}:**")
        for item in step.items:
            lines.append(f"   - {item}")
    lines.append("")

    lines.append("**Çözümün Avantajları:**")
    for adv in desc.advantages:
        lines.append(f"- {adv}")

    return "\n".join(lines)


def _h(text: str) -> str:
    return html.escape(text)


def format_summary_block(summary: str, problem: str) -> str:
    return f"<b>Özet:</b> {_h(summary)}<br><br><b>Problem:</b> {_h(problem)}"


def format_solution_steps_html(steps: list[SolutionStep]) -> str:
    lines: list[str] = []
    for step in steps:
        lines.append(f"• <b>{_h(step.title)}:</b> {_h(step.detail)}")
    return "<br>".join(lines)


def format_rich_solution_steps_html(sections: list[SolutionStepSection]) -> str:
    lines: list[str] = []
    for i, section in enumerate(sections, start=1):
        lines.append(f"<b>{i}. {_h(section.title)}</b>")
        for item in section.items:
            lines.append(f"&nbsp;&nbsp;• {_h(item)}")
    return "<br>".join(lines)


def format_advantages_html(advantages: list[str]) -> str:
    return "<br>".join(f"✓ {_h(adv)}" for adv in advantages)


def format_acceptance_criteria_html(criteria: list[str]) -> str:
    return "<br>".join(f"• {_h(item)}" for item in criteria)


def build_cards_payload(data: SendMessageInput, desc: TaskDescription | None = None) -> Payload:
    """Create Google Chat cards payload from SendMessageInput and optional TaskDescription.

    Args:
        data: Validate edilmiş SendMessageInput — domain, owner, participants vb.
        desc: Opsiyonel zengin açıklama (TaskDescription). Verilirse
              Muhtemel Çözüm bölümü zengin format kullanır; verilmezse
              data.resolved_steps() ile basit format kullanılır.

    Card yapısı:
        [Meta]         Alan / Tahmini Süre / Atanan / Katılımcılar
        [Görev]        Özet + Problem
        [Çözüm]        Muhtemel Çözüm adımları
        [Avantajlar]   Çözümün Avantajları  ← yalnızca desc verilirse
        [Kriterler]    Kabul Kriterleri
    """
    domain_info = data.resolved_domain()
    domain_label = domain_info.get("label", "Genel")

    sections: list[Payload] = []

    meta_widgets: list[Payload] = [
        {"keyValue": {"topLabel": "Alan", "content": _h(domain_label)}},
        {"keyValue": {"topLabel": "Tahmini Süre", "content": _h(data.estimated_duration)}},
    ]

    if data.task_owner:
        meta_widgets.append({"keyValue": {"topLabel": "Atanan", "content": _h(str(data.task_owner))}})

    if data.participants:
        meta_widgets.append({
            "keyValue": {
                "topLabel": "Katılımcılar",
                "content": _h(", ".join(data.participants)),
            }
        })

    sections.append({"widgets": meta_widgets})
    summary_text = (
        format_summary_block(desc.summary, desc.problem) if desc else format_summary_block(data.summary, data.problem)
    )
    sections.append({
        "header": "Görev Açıklaması",
        "widgets": [{"textParagraph": {"text": summary_text}}],
    })

    if desc and desc.solution_steps:
        solution_text = format_rich_solution_steps_html(desc.solution_steps)
    else:
        solution_text = format_solution_steps_html(data.resolved_steps())

    sections.append({
        "header": "Muhtemel Çözüm",
        "widgets": [{"textParagraph": {"text": solution_text}}],
    })

    if desc and desc.advantages:
        sections.append({
            "header": "Çözümün Avantajları",
            "widgets": [{"textParagraph": {"text": format_advantages_html(desc.advantages)}}],
        })

    sections.append({
        "header": "Kabul Kriterleri",
        "widgets": [{"textParagraph": {"text": format_acceptance_criteria_html(data.resolved_criteria())}}],
    })

    card = {"header": {"title": _h(data.title)}, "sections": sections}
    return {"cards": [card]}
