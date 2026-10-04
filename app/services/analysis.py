import logging

from pydantic import ValidationError

from app.schemas import AnalysisResult, Classification, LLMAnalysis, Sentiment
from app.services.actions import decide_action
from app.services.classifier import FallbackClassifier
from app.services.extraction import extract_entities
from app.services.llm import LLMClient
from app.services.rules import safety_rule

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm
        self.fallback = FallbackClassifier()

    async def analyze(self, *, subject: str | None, body: str) -> AnalysisResult:
        combined = f"{subject or ''}\n{body}"
        before = safety_rule(combined)
        if before:
            analysis = _rule_analysis(before.classification, before.reason, body)
            source = "deterministic_safety_rule"
        else:
            llm_analysis = await self._call_llm(subject=subject, body=body)
            source = "llm"
            if llm_analysis is None:
                analysis = await self.fallback.analyze(subject=subject, body=body)
                source = "deterministic_fallback"
            else:
                analysis = llm_analysis

            # A second pass guarantees critical language overrides any semantic result.
            after = safety_rule(combined)
            if after:
                analysis = _rule_analysis(after.classification, after.reason, body)
                source = "deterministic_safety_rule"

        decision = decide_action(analysis.classification)
        return AnalysisResult(
            **analysis.model_dump(),
            recommended_action=decision.action,
            requires_human_review=decision.requires_human_review,
            classifier_source=source,
        )

    async def _call_llm(self, *, subject: str | None, body: str) -> LLMAnalysis | None:
        if self.llm is None:
            return None
        try:
            candidate = await self.llm.analyze(subject=subject, body=body)
            return LLMAnalysis.model_validate(candidate) if candidate is not None else None
        except (ValidationError, TypeError, ValueError, KeyError):
            logger.warning("Invalid LLM result; using deterministic fallback", exc_info=True)
            return None


def _rule_analysis(classification: Classification, reason: str, body: str) -> LLMAnalysis:
    sentiment = (
        Sentiment.NEGATIVE if classification is Classification.UNSUBSCRIBE else Sentiment.NEUTRAL
    )
    return LLMAnalysis(
        classification=classification,
        confidence=0.99,
        sentiment=sentiment,
        reasoning_summary=reason,
        entities=extract_entities(body),
    )
