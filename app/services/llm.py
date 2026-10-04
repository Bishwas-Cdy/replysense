import json
import logging
from typing import Protocol

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.schemas import LLMAnalysis

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    async def analyze(self, *, subject: str | None, body: str) -> LLMAnalysis | None:
        """Return validated analysis, or None when model output cannot be trusted."""
        ...


class OpenAICompatibleClient:
    """Small OpenAI-compatible chat-completions adapter with a validation boundary."""

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model = settings.openai_model
        self.timeout = settings.llm_timeout_seconds

    async def analyze(self, *, subject: str | None, body: str) -> LLMAnalysis | None:
        if not self.api_key:
            return None
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps({"subject": subject or "", "body": body}),
                },
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return LLMAnalysis.model_validate_json(content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, ValidationError):
            logger.warning(
                "LLM analysis failed validation; using deterministic fallback", exc_info=True
            )
            return None


SYSTEM_PROMPT = """You classify inbound B2B sales email replies. Return one JSON object matching:
{
  "classification": one of INTERESTED, MEETING_REQUEST, QUESTION, NOT_NOW,
    NOT_INTERESTED, WRONG_PERSON, REFERRAL, OUT_OF_OFFICE, UNSUBSCRIBE, BOUNCE, UNKNOWN,
  "confidence": number from 0 to 1,
  "sentiment": one of positive, neutral, negative,
  "reasoning_summary": concise evidence-based sentence,
  "entities": {
    "dates": [verbatim explicit date strings],
    "relative_times": [verbatim relative time strings],
    "referred_contact": string or null,
    "referred_email": string or null,
    "question": string or null,
    "meeting_intent": string or null,
    "objection_reason": string or null,
    "company_name": string or null
  }
}
Do not invent information. Preserve ambiguous dates as written; never infer an exact date.
Treat meeting requests as MEETING_REQUEST, not merely INTERESTED.
"""
