"""Global FastAPI exception handlers for centralized error logging."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logger import StructuredLogger, get_logger
from app.utils.request_context import get_request_context

_LOGGER: StructuredLogger = get_logger("app.core.exception_handlers")


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global handlers to log API and runtime failures."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        _LOGGER.event(
            event="http_exception",
            message="HTTP exception raised",
            path=request.url.path,
            method=request.method,
            status=exc.status_code,
            detail=exc.detail,
        )
        context = get_request_context()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "request_id": context.request_id,
                "trace_id": context.trace_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        _LOGGER.event(
            event="validation_error",
            message="Request validation failed",
            path=request.url.path,
            method=request.method,
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            errors=exc.errors(),
        )
        context = get_request_context()
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": exc.errors(),
                "request_id": context.request_id,
                "trace_id": context.trace_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        _LOGGER.exception_event(
            event="unhandled_exception",
            message="Unhandled server exception",
            path=request.url.path,
            method=request.method,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type=type(exc).__name__,
        )
        context = get_request_context()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "request_id": context.request_id,
                "trace_id": context.trace_id,
            },
        )

