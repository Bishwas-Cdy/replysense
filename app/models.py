from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InboundReply(Base):
    __tablename__ = "inbound_replies"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(998), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    analysis: Mapped["ReplyAnalysis | None"] = relationship(back_populates="reply")


class ReplyAnalysis(Base):
    __tablename__ = "reply_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    reply_id: Mapped[int] = mapped_column(ForeignKey("inbound_replies.id"), unique=True)
    classification: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float] = mapped_column(Float)
    sentiment: Mapped[str] = mapped_column(String(20))
    reasoning_summary: Mapped[str] = mapped_column(Text)
    extracted_entities: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    recommended_action: Mapped[str] = mapped_column(String(50))
    requires_human_review: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reply: Mapped[InboundReply] = relationship(back_populates="analysis")
    suggested_reply: Mapped["SuggestedReply | None"] = relationship(back_populates="analysis")


class SuggestedReply(Base):
    __tablename__ = "suggested_replies"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("reply_analyses.id"), unique=True)
    subject: Mapped[str] = mapped_column(String(998))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    analysis: Mapped[ReplyAnalysis] = relationship(back_populates="suggested_reply")
