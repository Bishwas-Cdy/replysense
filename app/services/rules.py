import re
from dataclasses import dataclass

from app.schemas import Classification


@dataclass(frozen=True)
class RuleMatch:
    classification: Classification
    reason: str


UNSUBSCRIBE_PATTERNS = (
    r"\bunsubscribe\b",
    r"\bremove me\b",
    r"\bstop (?:emailing|contacting|messaging) me\b",
    r"\btake me off (?:your|the) (?:list|mailing list)\b",
    r"\bdo not contact me\b",
    r"\bdon't contact me\b",
    r"\bopt[ -]?out\b",
)
BOUNCE_PATTERNS = (
    r"\baddress not found\b",
    r"\bmailbox (?:is )?unavailable\b",
    r"\buser unknown\b",
    r"\brecipient (?:address )?rejected\b",
    r"\b550[ -]5\.1\.1\b",
    r"\bundeliver(?:able|ed)\b",
    r"\bdelivery (?:status notification|failed|failure)\b",
)
OOO_PATTERNS = (
    r"\bout of (?:the )?office\b",
    r"\bautomatic reply\b",
    r"\bauto(?:matic)?[ -]?response\b",
    r"\baway from (?:my )?(?:email|office)\b",
    r"\bon (?:annual )?leave\b",
    r"\breturning (?:on|to the office)\b",
)


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def safety_rule(text: str) -> RuleMatch | None:
    """Return safety-critical classification in strict precedence order."""
    if _matches(UNSUBSCRIBE_PATTERNS, text):
        return RuleMatch(Classification.UNSUBSCRIBE, "Explicit request to stop contact detected.")
    if _matches(BOUNCE_PATTERNS, text):
        return RuleMatch(Classification.BOUNCE, "Delivery failure language detected.")
    if _matches(OOO_PATTERNS, text):
        return RuleMatch(Classification.OUT_OF_OFFICE, "Automatic out-of-office language detected.")
    return None
