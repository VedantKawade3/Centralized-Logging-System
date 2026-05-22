"""Reusable logger helpers for structured event logging."""

from __future__ import annotations

import logging
import os
from typing import Any


class StructuredLogger(logging.LoggerAdapter):
    """Logger adapter with event-focused helper methods."""

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        extra = kwargs.get("extra")
        if extra is None:
            extra = {}
            kwargs["extra"] = extra
        elif not isinstance(extra, dict):
            extra = {"raw_extra": str(extra)}
            kwargs["extra"] = extra

        extra.setdefault("service", self.extra.get("service"))
        extra.setdefault("module_name", self.extra.get("module_name"))
        return msg, kwargs

    def event(
        self,
        event: str,
        message: str,
        *,
        level: int = logging.INFO,
        **fields: Any,
    ) -> None:
        """Emit a structured business event."""
        extra = {"event": event, **fields}
        self.log(level=level, msg=message, extra=extra)

    def audit(
        self,
        event: str,
        message: str,
        *,
        level: int = logging.INFO,
        **fields: Any,
    ) -> None:
        """Emit an audit event routed to `audit.log`."""
        extra = {"event": event, "channel": "audit", **fields}
        self.log(level=level, msg=message, extra=extra)

    def exception_event(
        self,
        event: str,
        message: str,
        **fields: Any,
    ) -> None:
        """Emit an error event with traceback."""
        extra = {"event": event, **fields}
        self.error(msg=message, extra=extra, exc_info=True)

    def lifecycle(
        self,
        event: str,
        *,
        session_status: str,
        message: str,
        level: int = logging.INFO,
        **fields: Any,
    ) -> None:
        """Emit lifecycle events aligned to orchestration state machines."""
        extra = {"event": event, "interview_status": session_status, **fields}
        self.log(level=level, msg=message, extra=extra)


def get_logger(module_name: str) -> StructuredLogger:
    """Return a structured logger for the given module."""
    base_logger = logging.getLogger(module_name)
    return StructuredLogger(
        logger=base_logger,
        extra={
            "service": os.getenv("SERVICE_NAME", "interview_service"),
            "module_name": module_name,
        },
    )
