"""Utilities for propagating request/trace/session identifiers across services."""

from __future__ import annotations

from collections.abc import MutableMapping

from app.integration.contracts import REQUEST_ID_HEADER, SESSION_ID_HEADER, TRACE_ID_HEADER
from app.utils.request_context import get_request_context


def build_correlation_headers() -> dict[str, str]:
    """Build outbound headers from current request context."""
    context = get_request_context()
    headers: dict[str, str] = {}
    if context.request_id:
        headers[REQUEST_ID_HEADER] = str(context.request_id)
    if context.trace_id:
        headers[TRACE_ID_HEADER] = str(context.trace_id)
    if context.session_id:
        headers[SESSION_ID_HEADER] = str(context.session_id)
    return headers


def inject_correlation_headers(headers: MutableMapping[str, str] | None = None) -> dict[str, str]:
    """Merge correlation headers into an existing mutable headers object."""
    resolved = dict(headers or {})
    resolved.update(build_correlation_headers())
    return resolved

