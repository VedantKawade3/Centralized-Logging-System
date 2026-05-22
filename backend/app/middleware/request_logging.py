"""FastAPI middleware for request/response logging and correlation IDs."""

from __future__ import annotations

import os
import re
from time import perf_counter
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import StructuredLogger, get_logger
from app.integration.contracts import REQUEST_ID_HEADER, SESSION_ID_HEADER, TRACE_ID_HEADER
from app.utils.request_context import bind_request_context, new_correlation_id, reset_request_context


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request lifecycle with latency and correlation metadata."""

    def __init__(self, app: Callable, service_name: str | None = None) -> None:
        super().__init__(app)
        self.service_name = service_name or os.getenv("SERVICE_NAME", "interview_service")
        self.logger: StructuredLogger = get_logger("app.middleware.request_logging")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or new_correlation_id()
        trace_id = request.headers.get(TRACE_ID_HEADER) or request_id
        session_id = self._extract_session_id(request)

        tokens = bind_request_context(
            request_id=request_id,
            trace_id=trace_id,
            session_id=session_id,
            service=self.service_name,
        )

        start = perf_counter()
        status_code = 500
        failed = False
        response: Response | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[TRACE_ID_HEADER] = trace_id
            if session_id:
                response.headers[SESSION_ID_HEADER] = str(session_id)
            return response
        except Exception:
            failed = True
            duration_ms = round((perf_counter() - start) * 1000, 3)
            self.logger.exception_event(
                event="http_request_exception",
                message="Unhandled exception during request processing",
                method=request.method,
                path=request.url.path,
                status=status_code,
                duration_ms=duration_ms,
                client_ip=request.client.host if request.client else None,
                query=str(request.url.query) if request.url.query else None,
            )
            raise
        finally:
            duration_ms = round((perf_counter() - start) * 1000, 3)
            self.logger.event(
                event="http_request",
                message="HTTP request processed",
                method=request.method,
                path=request.url.path,
                endpoint=request.url.path,
                status=status_code,
                duration_ms=duration_ms,
                request_id=request_id,
                trace_id=trace_id,
                session_id=session_id,
                success=not failed,
            )
            reset_request_context(tokens)

    @staticmethod
    def _extract_session_id(request: Request) -> str | None:
        header_session = request.headers.get(SESSION_ID_HEADER)
        if header_session:
            return header_session

        query_session = request.query_params.get("session_id")
        if query_session:
            return query_session

        # Matches patterns like: /session/123/start or /session/session_abc/status
        match = re.search(r"/session/([^/]+)", request.url.path)
        if match:
            return match.group(1)
        return None
