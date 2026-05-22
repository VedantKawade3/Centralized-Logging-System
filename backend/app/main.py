"""Example FastAPI integration for the centralized logging framework."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.core.exception_handlers import register_exception_handlers
from app.core.logger import get_logger
from app.core.logging_config import configure_logging
from app.integration.contracts import InterviewEvent, InterviewStage, SessionStatus
from app.middleware.request_logging import RequestLoggingMiddleware
from app.tracing.event_tracer import EventTracer
from app.utils.request_context import set_session_id

configure_logging()

app = FastAPI(title="Centralized Logging System")
app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)

logger = get_logger("app.main")
tracer = EventTracer("app.tracing.interview_pipeline")


class InterviewStartRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)


@app.get("/health")
async def health_check() -> dict[str, str]:
    logger.event(event="health_check", message="Health endpoint called", status="ok")
    return {"status": "ok"}


@app.post("/interview/start")
async def start_interview(payload: InterviewStartRequest) -> dict[str, str]:
    set_session_id(payload.session_id)
    tracer.session_status(
        session_status=SessionStatus.CREATED,
        message="Interview session created",
        session_id=payload.session_id,
        candidate_id=payload.candidate_id,
    )
    tracer.session_status(
        session_status=SessionStatus.QUEUED,
        message="Interview session queued",
        session_id=payload.session_id,
        candidate_id=payload.candidate_id,
    )
    logger.audit(
        event=InterviewEvent.SESSION_STARTED,
        message="Interview session started",
        session_id=payload.session_id,
        candidate_id=payload.candidate_id,
        status="success",
    )

    async with tracer.trace_stage_async(
        stage=InterviewStage.QUESTION_GENERATION,
        session_id=payload.session_id,
        module="gpt_question_engine",
        candidate_id=payload.candidate_id,
    ):
        await asyncio.sleep(0.01)
        tracer.emit(
            event=InterviewEvent.QUESTION_GENERATED,
            message="Interview question generated",
            session_id=payload.session_id,
            module="gpt_question_engine",
            status="success",
            candidate_id=payload.candidate_id,
            question_id="Q1",
        )

    async with tracer.trace_stage_async(
        stage=InterviewStage.EVALUATION,
        session_id=payload.session_id,
        module="evaluation_engine",
        candidate_id=payload.candidate_id,
        question_id="Q1",
    ):
        await asyncio.sleep(0.01)
        tracer.emit(
            event=InterviewEvent.EVALUATION_COMPLETED,
            message="Candidate response evaluated",
            session_id=payload.session_id,
            module="evaluation_engine",
            status="success",
            risk_score=0.08,
            candidate_id=payload.candidate_id,
            question_id="Q1",
        )

    tracer.session_status(
        session_status=SessionStatus.COMPLETED,
        message="Interview session lifecycle completed",
        session_id=payload.session_id,
        candidate_id=payload.candidate_id,
    )
    logger.event(
        event="session_ready",
        message="Interview pipeline initialized",
        session_id=payload.session_id,
        status="success",
    )
    return {
        "message": "Interview session started",
        "session_id": payload.session_id,
    }


@app.get("/demo/error")
async def raise_example_error() -> None:
    raise RuntimeError("Simulated runtime failure for logging demonstration")
