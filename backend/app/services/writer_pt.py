"""Writer — generates draft content in multiple formats."""
from typing import Optional
from .llm_client import LLMClient
import json


class Writer:
    """Generates drafts for approved events (X thread, site card, newsletter)."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    async def generate_drafts(
        self,
        event_title: str,
        summary: str,
        evidence: list[dict],
        risk_flags: list[str],
    ) -> dict:
        """Generate all three draft formats."""
        prompt = f"""Generate 3 draft formats for this media investigation. Include evidence references and appropriate uncertainty language.

Event: {event_title}
Summary: {summary}
Evidence: {json.dumps(evidence)}
Risk flags: {json.dumps(risk_flags)}

Return JSON with exactly these keys:
- x_thread: {{"content": "...", "evidence_references": [...], "uncertainty_language": "..."}}
- site_card: {{"content": "...", "evidence_references": [...], "uncertainty_language": "..."}}
- newsletter_snippet: {{"content": "...", "evidence_references": [...], "uncertainty_language": "..."}}

Rules:
- Never make direct accusations when evidence is weak
- Include "According to [source]" phrasing for claims
- Reference evidence URLs
- Use uncertainty language like "suggests", "indicates", "reportedly" for unconfirmed claims"""

        result = await self.llm.chat([{"role": "user", "content": prompt}], temperature=0.4, json_mode=True)
        return json.loads(result)