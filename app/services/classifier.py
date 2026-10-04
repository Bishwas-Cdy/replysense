import re

from app.schemas import Classification, LLMAnalysis, Sentiment
from app.services.extraction import extract_entities


class FallbackClassifier:
    """Conservative keyword classifier used when no valid LLM result is available."""

    async def analyze(self, *, subject: str | None, body: str) -> LLMAnalysis:
        del subject
        classification, confidence, sentiment, reason = _classify(body)
        return LLMAnalysis(
            classification=classification,
            confidence=confidence,
            sentiment=sentiment,
            reasoning_summary=reason,
            entities=extract_entities(body),
        )


def _classify(text: str) -> tuple[Classification, float, Sentiment, str]:
    lowered = text.lower()
    if re.search(r"\b(wrong person|not the right person|not my area|don't handle)\b", lowered):
        if re.search(r"\b(contact|reach out|speak to|email)\b", lowered) or re.search(
            r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", lowered
        ):
            return (
                Classification.REFERRAL,
                0.87,
                Sentiment.NEUTRAL,
                "The recipient redirected the conversation to another contact.",
            )
        return (
            Classification.WRONG_PERSON,
            0.86,
            Sentiment.NEUTRAL,
            "The recipient indicated they are not the appropriate contact.",
        )
    if re.search(r"\b(?:not (?:right )?now|check back|reach back|later|next quarter)\b", lowered):
        return (
            Classification.NOT_NOW,
            0.88,
            Sentiment.NEUTRAL,
            "The prospect deferred the conversation to a later time.",
        )
    if re.search(r"\b(?:meet|meeting|demo|call|calendar|schedule|show me)\b", lowered):
        return (
            Classification.MEETING_REQUEST,
            0.88,
            Sentiment.POSITIVE,
            "The prospect expressed intent to arrange a meeting or demonstration.",
        )
    if "?" in text or re.search(r"\b(?:how|what|when|where|why|can you|could you)\b", lowered):
        return (
            Classification.QUESTION,
            0.78,
            Sentiment.NEUTRAL,
            "The reply contains a question requiring a response.",
        )
    if re.search(r"\b(?:interested|sounds (?:good|useful|interesting)|tell me more)\b", lowered):
        return (
            Classification.INTERESTED,
            0.84,
            Sentiment.POSITIVE,
            "The prospect expressed positive interest.",
        )
    if re.search(r"\b(?:not interested|no thanks|no thank you|pass on this)\b", lowered):
        return (
            Classification.NOT_INTERESTED,
            0.88,
            Sentiment.NEGATIVE,
            "The prospect declined the offering.",
        )
    return (
        Classification.UNKNOWN,
        0.35,
        Sentiment.NEUTRAL,
        "The deterministic fallback found no reliable intent signal.",
    )
