"""Risk reviewer — evaluates risk flags and scores for the drafting gate."""
from typing import Optional
from .llm_client import LLMClient
from ..core.state_machine import BLOCKING_RISK_FLAGS
import json


class RiskReviewer:
    """Assesses risk for an event and determines drafting gate eligibility."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    async def review(self, event_data: dict, research_data: Optional[dict] = None) -> dict:
        """Review event for risk flags and assign scores."""
        prompt = f"""Assess risk for this media investigation event:

Event data: {json.dumps(event_data)}
Research: {json.dumps(research_data) if research_data else "None"}

Consider these blocking flags:
{json.dumps(list(BLOCKING_RISK_FLAGS))}

Return JSON with:
- reliability_score: 0-5 (how reliable is the evidence?)
- undercoverage_score: 0-5 (how undercovered is this story?)
- flags: list of applicable risk flags
- blocking_flags: subset of flags that are blocking (see list above)
- rationale: detailed explanation"""

        result = await self.llm.chat([{"role": "user", "content": prompt}], temperature=0.2, json_mode=True)
        return json.loads(result)