"""Shared integration contracts aligned to internship backend repositories."""

from __future__ import annotations

from dataclasses import dataclass

# Common correlation headers expected to flow between services.
REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"
SESSION_ID_HEADER = "X-Session-ID"


class SessionStatus:
    """Session states seen across interview orchestration modules."""

    CREATED = "CREATED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    VIDEO_PROCESSING = "VIDEO_PROCESSING"
    AUDIO_PROCESSING = "AUDIO_PROCESSING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class InterviewEvent:
    """Event names used across integrated AI interview lifecycle services."""

    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    QUESTION_GENERATED = "question_generated"
    STT_TRANSCRIPT_RECEIVED = "transcript_received"
    EVALUATION_COMPLETED = "evaluation_completed"
    RISK_SCORE_GENERATED = "risk_score_generated"
    STT_FAILED = "stt_failed"
    LLM_TIMEOUT = "llm_timeout"
    WORKER_ASSIGNED = "worker_assigned"
    WORKER_HEARTBEAT = "worker_heartbeat"
    PROCTOR_EVENT = "proctor_event"


class InterviewStage:
    """Pipeline stages observed in the orchestration worker/task layer."""

    QUESTION_GENERATION = "question_generation"
    VIDEO_ANALYSIS = "video_analysis"
    AUDIO_ANALYSIS = "audio_analysis"
    EVALUATION = "evaluation"
    RISK_SCORING = "risk_scoring"


@dataclass(frozen=True)
class StandardLogKeys:
    """Required keys for ecosystem-wide structured observability logs."""

    timestamp: str = "timestamp"
    level: str = "level"
    service: str = "service"
    module: str = "module"
    event: str = "event"
    session_id: str = "session_id"
    request_id: str = "request_id"
    trace_id: str = "trace_id"
    latency_ms: str = "latency_ms"
    status: str = "status"
    message: str = "message"

