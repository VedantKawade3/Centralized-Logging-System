"""Helpers to trace interview lifecycle events with correlation IDs."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager, contextmanager
from time import perf_counter
from typing import Any, AsyncIterator, Iterator

from app.core.logger import StructuredLogger, get_logger
from app.integration.contracts import SessionStatus


INTERVIEW_EVENTS = {
    "interview_started",
    "question_generated",
    "transcript_received",
    "evaluation_completed",
    "risk_score_generated",
    "session_ended",
    "stt_failed",
    "llm_timeout",
}


class EventTracer:
    """Utility for consistent business-event and stage tracing logs."""

    def __init__(self, module_name: str) -> None:
        self.logger: StructuredLogger = get_logger(module_name)

    def emit(
        self,
        *,
        event: str,
        message: str,
        level: int = logging.INFO,
        **fields: Any,
    ) -> None:
        self.logger.event(event=event, message=message, level=level, **fields)

    @contextmanager
    def trace_stage(
        self,
        *,
        stage: str,
        message: str | None = None,
        **fields: Any,
    ) -> Iterator[None]:
        """Track start/success/failure for sync service sections."""
        start = perf_counter()
        self.emit(
            event=f"{stage}_start",
            message=message or f"{stage} started",
            stage=stage,
            status="start",
            **fields,
        )
        try:
            yield
        except Exception:
            latency_ms = round((perf_counter() - start) * 1000, 3)
            self.logger.exception_event(
                event=f"{stage}_failed",
                message=f"{stage} failed",
                stage=stage,
                status="failed",
                latency_ms=latency_ms,
                **fields,
            )
            raise
        else:
            latency_ms = round((perf_counter() - start) * 1000, 3)
            self.emit(
                event=f"{stage}_completed",
                message=f"{stage} completed",
                stage=stage,
                status="success",
                latency_ms=latency_ms,
                **fields,
            )

    def session_status(
        self,
        *,
        session_status: str,
        message: str,
        event: str = "session_state_updated",
        **fields: Any,
    ) -> None:
        """Emit standardized session lifecycle status updates."""
        normalized = session_status.upper()
        if normalized not in {
            SessionStatus.CREATED,
            SessionStatus.QUEUED,
            SessionStatus.PROCESSING,
            SessionStatus.VIDEO_PROCESSING,
            SessionStatus.AUDIO_PROCESSING,
            SessionStatus.EVALUATING,
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.TIMEOUT,
            SessionStatus.CANCELLED,
        }:
            normalized = session_status
        self.logger.lifecycle(
            event=event,
            session_status=normalized,
            message=message,
            **fields,
        )

    @asynccontextmanager
    async def trace_stage_async(
        self,
        *,
        stage: str,
        message: str | None = None,
        **fields: Any,
    ) -> AsyncIterator[None]:
        """Track start/success/failure for async service sections."""
        start = perf_counter()
        self.emit(
            event=f"{stage}_start",
            message=message or f"{stage} started",
            stage=stage,
            status="start",
            **fields,
        )
        try:
            yield
        except Exception:
            latency_ms = round((perf_counter() - start) * 1000, 3)
            self.logger.exception_event(
                event=f"{stage}_failed",
                message=f"{stage} failed",
                stage=stage,
                status="failed",
                latency_ms=latency_ms,
                **fields,
            )
            raise
        else:
            latency_ms = round((perf_counter() - start) * 1000, 3)
            self.emit(
                event=f"{stage}_completed",
                message=f"{stage} completed",
                stage=stage,
                status="success",
                latency_ms=latency_ms,
                **fields,
            )
