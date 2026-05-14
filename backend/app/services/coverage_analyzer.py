"""Coverage analyzer — compares event against mainstream Portuguese outlets."""
from typing import Optional
from .llm_client import LLMClient
import json


class CoverageAnalyzer:
    """Analyzes mainstream media coverage for an event."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    async def analyze(self, event_title: str, event_summary: str, outlets: list[dict]) -> dict:
        """Compare event against a list of outlets and return coverage analysis."""
        prompt = f"""Compare this event against Portuguese media outlets:

Event: {event_title}
Summary: {event_summary}

Outlets to check: {json.dumps(outlets)}

Return JSON with:
- coverage_found: list of outlets that covered it with article_url, article_title, framing_difference
- coverage_gaps: list of outlets that didn't cover it
- undercoverage_score: 0-5 (5 = severely undercovered)
- overall_assessment: brief analysis"""

        result = await self.llm.chat([{"role": "user", "content": prompt}], temperature=0.2)
        return json.loads(result)