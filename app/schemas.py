from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Classification(StrEnum):
    INTERESTED = "INTERESTED"
    MEETING_REQUEST = "MEETING_REQUEST"
    QUESTION = "QUESTION"
    NOT_NOW = "NOT_NOW"
    NOT_INTERESTED = "NOT_INTERESTED"
    WRONG_PERSON = "WRONG_PERSON"
    REFERRAL = "REFERRAL"
    OUT_OF_OFFICE = "OUT_OF_OFFICE"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    BOUNCE = "BOUNCE"
    UNKNOWN = "UNKNOWN"


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class RecommendedAction(StrEnum):
    HUMAN_REVIEW = "HUMAN_REVIEW"
    SCHEDULE_FOLLOW_UP = "SCHEDULE_FOLLOW_UP"
    ANSWER_QUESTION = "ANSWER_QUESTION"
    CREATE_FOLLOW_UP_TASK = "CREATE_FOLLOW_UP_TASK"
    CLOSE_OPPORTUNITY = "CLOSE_OPPORTUNITY"
    FIND_CORRECT_CONTACT = "FIND_CORRECT_CONTACT"
    ROUTE_TO_REFERRAL = "ROUTE_TO_REFERRAL"
    WAIT_UNTIL_RETURN = "WAIT_UNTIL_RETURN"
    SUPPRESS_CONTACT = "SUPPRESS_CONTACT"
    MARK_EMAIL_INVALID = "MARK_EMAIL_INVALID"
    MANUAL_TRIAGE = "MANUAL_TRIAGE"


class ReplyCreate(BaseModel):
    from_email: EmailStr | None = None
    subject: str | None = Field(default=None, max_length=998)
    body: str = Field(min_length=1, max_length=100_000)
    received_at: datetime | None = None

    @field_validator("body")
    @classmethod
    def reject_blank_body(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("body must not be blank")
        return value


class ExtractedEntities(BaseModel):
    dates: list[str] = Field(default_factory=list)
    relative_times: list[str] = Field(default_factory=list)
    referred_contact: str | None = None
    referred_email: EmailStr | None = None
    question: str | None = None
    meeting_intent: str | None = None
    objection_reason: str | None = None
    company_name: str | None = None


class LLMAnalysis(BaseModel):
    classification: Classification
    confidence: float = Field(ge=0, le=1)
    sentiment: Sentiment
    reasoning_summary: str = Field(min_length=1, max_length=500)
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)


class AnalysisResult(LLMAnalysis):
    recommended_action: RecommendedAction
    requires_human_review: bool
    classifier_source: str


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reply_id: int
    classification: Classification
    confidence: float
    sentiment: Sentiment
    reasoning_summary: str
    extracted_entities: dict[str, Any]
    recommended_action: RecommendedAction
    requires_human_review: bool
    created_at: datetime


class ReplyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_email: str | None
    subject: str | None
    body: str
    received_at: datetime


class ReplyDetail(ReplyRead):
    analysis: AnalysisRead | None = None


class SuggestedReplyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_id: int
    subject: str
    body: str
    created_at: datetime


class AnalyzeResponse(BaseModel):
    reply: ReplyRead
    analysis: AnalysisRead


class WebhookResponse(BaseModel):
    reply_id: int
    analysis_id: int
    classification: Classification
    confidence: float
    sentiment: Sentiment
    entities: dict[str, Any]
    recommended_action: RecommendedAction
    requires_human_review: bool
    reasoning_summary: str
