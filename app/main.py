import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database import Base, build_engine
from app.models import InboundReply, ReplyAnalysis, SuggestedReply
from app.schemas import (
    AnalysisRead,
    AnalyzeResponse,
    ReplyCreate,
    ReplyDetail,
    ReplyRead,
    SuggestedReplyRead,
    WebhookResponse,
)
from app.services.analysis import AnalysisService
from app.services.llm import LLMClient, OpenAICompatibleClient
from app.services.personalization import build_suggested_reply

logger = logging.getLogger(__name__)


def create_app(
    *,
    settings: Settings | None = None,
    llm_client: LLMClient | None = None,
    engine: Engine | None = None,
) -> FastAPI:
    runtime_settings = settings or get_settings()
    runtime_engine = engine or build_engine(runtime_settings.database_url)
    session_factory = sessionmaker(bind=runtime_engine, expire_on_commit=False)
    llm = llm_client or OpenAICompatibleClient(runtime_settings)
    analysis_service = AnalysisService(llm)

    logging.basicConfig(
        level=getattr(logging, runtime_settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        Base.metadata.create_all(runtime_engine)
        logger.info("ReplySense started")
        yield

    application = FastAPI(
        title="ReplySense",
        version="0.1.0",
        description=(
            "AI-assisted inbound sales reply intelligence with deterministic safety overrides."
        ),
        lifespan=lifespan,
    )
    application.state.analysis_service = analysis_service

    async def get_session() -> AsyncIterator[Session]:
        with session_factory() as session:
            yield session

    SessionDep = Annotated[Session, Depends(get_session)]

    @application.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "replysense"}

    @application.post(
        "/replies/analyze",
        response_model=AnalyzeResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["replies"],
    )
    async def analyze_reply(
        payload: ReplyCreate, request: Request, db: SessionDep
    ) -> AnalyzeResponse:
        reply, analysis = await _analyze_and_save(payload, request, db)
        return AnalyzeResponse(
            reply=ReplyRead.model_validate(reply),
            analysis=AnalysisRead.model_validate(analysis),
        )

    @application.get("/replies", response_model=list[ReplyRead], tags=["replies"])
    async def list_replies(db: SessionDep) -> list[InboundReply]:
        return list(db.scalars(select(InboundReply).order_by(InboundReply.id.desc())).all())

    @application.get("/replies/{reply_id}", response_model=ReplyDetail, tags=["replies"])
    async def get_reply(reply_id: int, db: SessionDep) -> InboundReply:
        reply = db.get(InboundReply, reply_id)
        if reply is None:
            raise HTTPException(status_code=404, detail="Reply not found")
        return reply

    @application.get("/replies/{reply_id}/analysis", response_model=AnalysisRead, tags=["replies"])
    async def get_analysis(reply_id: int, db: SessionDep) -> ReplyAnalysis:
        analysis = db.scalar(select(ReplyAnalysis).where(ReplyAnalysis.reply_id == reply_id))
        if analysis is None:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return analysis

    @application.post(
        "/replies/{reply_id}/suggest-response",
        response_model=SuggestedReplyRead,
        status_code=status.HTTP_201_CREATED,
        tags=["replies"],
    )
    async def suggest_response(reply_id: int, db: SessionDep) -> SuggestedReply:
        reply = db.get(InboundReply, reply_id)
        if reply is None:
            raise HTTPException(status_code=404, detail="Reply not found")
        analysis = db.scalar(select(ReplyAnalysis).where(ReplyAnalysis.reply_id == reply_id))
        if analysis is None:
            raise HTTPException(status_code=404, detail="Analysis not found")
        existing = db.scalar(
            select(SuggestedReply).where(SuggestedReply.analysis_id == analysis.id)
        )
        if existing:
            return existing
        draft = build_suggested_reply(reply, analysis)
        if draft is None:
            raise HTTPException(
                status_code=409,
                detail="Suggested responses are disabled for this classification",
            )
        suggested = SuggestedReply(analysis_id=analysis.id, subject=draft[0], body=draft[1])
        db.add(suggested)
        db.commit()
        db.refresh(suggested)
        return suggested

    @application.post(
        "/webhooks/reply",
        response_model=WebhookResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["automation"],
    )
    async def webhook_reply(
        payload: ReplyCreate, request: Request, db: SessionDep
    ) -> WebhookResponse:
        reply, analysis = await _analyze_and_save(payload, request, db)
        return WebhookResponse(
            reply_id=reply.id,
            analysis_id=analysis.id,
            classification=analysis.classification,
            confidence=analysis.confidence,
            sentiment=analysis.sentiment,
            entities=analysis.extracted_entities,
            recommended_action=analysis.recommended_action,
            requires_human_review=analysis.requires_human_review,
            reasoning_summary=analysis.reasoning_summary,
        )

    return application


async def _analyze_and_save(
    payload: ReplyCreate, request: Request, db: Session
) -> tuple[InboundReply, ReplyAnalysis]:
    service: AnalysisService = request.app.state.analysis_service
    result = await service.analyze(subject=payload.subject, body=payload.body)
    reply = InboundReply(
        from_email=str(payload.from_email) if payload.from_email else None,
        subject=payload.subject,
        body=payload.body,
    )
    if payload.received_at is not None:
        reply.received_at = payload.received_at
    db.add(reply)
    db.flush()
    analysis = ReplyAnalysis(
        reply_id=reply.id,
        classification=result.classification.value,
        confidence=result.confidence,
        sentiment=result.sentiment.value,
        reasoning_summary=result.reasoning_summary,
        extracted_entities=result.entities.model_dump(mode="json", exclude_none=True),
        recommended_action=result.recommended_action.value,
        requires_human_review=result.requires_human_review,
    )
    db.add(analysis)
    db.commit()
    db.refresh(reply)
    db.refresh(analysis)
    logger.info(
        "Analyzed reply id=%s classification=%s source=%s",
        reply.id,
        result.classification,
        result.classifier_source,
    )
    return reply, analysis


app = create_app()
