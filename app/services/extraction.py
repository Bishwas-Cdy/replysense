import re

from app.schemas import ExtractedEntities

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
RELATIVE_PATTERNS = (
    rf"\b(?:next|this|later this) (?:week|month|quarter|{MONTHS})\b",
    r"\b(?:tomorrow|next year|in a few (?:days|weeks|months))\b",
)
DATE_PATTERN = rf"\b(?:{MONTHS})(?:\s+\d{{1,2}}(?:,\s*\d{{4}})?)?\b"
EMAIL_PATTERN = r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"


def extract_entities(text: str) -> ExtractedEntities:
    relative_times = [
        match.group(0)
        for pattern in RELATIVE_PATTERNS
        for match in re.finditer(pattern, text, re.I)
    ]
    dates = [match.group(0) for match in re.finditer(DATE_PATTERN, text, re.I)]
    emails = re.findall(EMAIL_PATTERN, text, re.I)
    question_match = re.search(r"([^.!?]*\?)(?:\s|$)", text)
    referral = re.search(
        r"(?:contact|reach out to|speak (?:with|to)|try)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        text,
        re.I,
    )
    company = re.search(r"\b(?:at|from)\s+([A-Z][A-Za-z0-9&.-]+(?:\s+[A-Z][A-Za-z0-9&.-]+)*)", text)
    return ExtractedEntities(
        dates=dates,
        relative_times=relative_times,
        referred_contact=referral.group(1) if referral else None,
        referred_email=emails[0] if emails else None,
        question=question_match.group(1).strip() if question_match else None,
        meeting_intent=_meeting_phrase(text),
        objection_reason=_objection(text),
        company_name=company.group(1) if company else None,
    )


def _meeting_phrase(text: str) -> str | None:
    match = re.search(
        r"[^.!?]*(?:meet|meeting|demo|call|calendar|schedule|show me)[^.!?]*[.!?]?", text, re.I
    )
    return match.group(0).strip() if match else None


def _objection(text: str) -> str | None:
    match = re.search(r"\b(?:because|since|due to)\s+([^.!?]+)", text, re.I)
    return match.group(1).strip() if match else None
