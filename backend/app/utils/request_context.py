"""Per-request correlation context shared across async call stacks."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
_trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)
_session_id_ctx: ContextVar[str | None] = ContextVar("session_id", default=None)
_service_ctx: ContextVar[str | None] = ContextVar("service", default=None)


@dataclass(frozen=True)
class RequestContext:
    """Resolved correlation values for the current request/task."""

    request_id: str | None
    trace_id: str | None
    session_id: str | None
    service: str | None


@dataclass(frozen=True)
class ContextTokens:
    """Context variable tokens used to safely reset request state."""

    request_id: Token[str | None]
    trace_id: Token[str | None]
    session_id: Token[str | None]
    service: Token[str | None]


def new_correlation_id() -> str:
    """Return a random request/trace identifier."""
    return uuid4().hex


def bind_request_context(
    *,
    request_id: str | None,
    trace_id: str | None,
    session_id: str | None,
    service: str | None,
) -> ContextTokens:
    """Attach request-scoped context to the current async execution path."""
    resolved_request_id = request_id or new_correlation_id()
    resolved_trace_id = trace_id or resolved_request_id
    return ContextTokens(
        request_id=_request_id_ctx.set(resolved_request_id),
        trace_id=_trace_id_ctx.set(resolved_trace_id),
        session_id=_session_id_ctx.set(session_id),
        service=_service_ctx.set(service),
    )


def reset_request_context(tokens: ContextTokens) -> None:
    """Reset context variables after request completion."""
    _request_id_ctx.reset(tokens.request_id)
    _trace_id_ctx.reset(tokens.trace_id)
    _session_id_ctx.reset(tokens.session_id)
    _service_ctx.reset(tokens.service)


def set_session_id(session_id: str | None) -> Token[str | None]:
    """Update session ID after payload parsing when needed."""
    return _session_id_ctx.set(session_id)


def get_request_context() -> RequestContext:
    """Read request context for the active async task/thread."""
    return RequestContext(
        request_id=_request_id_ctx.get(),
        trace_id=_trace_id_ctx.get(),
        session_id=_session_id_ctx.get(),
        service=_service_ctx.get(),
    )


def get_request_context_dict() -> dict[str, Any]:
    """Return context values in dict form for logger filters/formatters."""
    context = get_request_context()
    return {
        "request_id": context.request_id,
        "trace_id": context.trace_id,
        "session_id": context.session_id,
        "service": context.service,
    }

