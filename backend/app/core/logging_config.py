"""Central logging configuration with async-safe queue processing."""

from __future__ import annotations

import atexit
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from queue import Queue
from threading import Lock
from typing import Any

try:
    from pythonjsonlogger.json import JsonFormatter
except ImportError:  # pragma: no cover - compatibility with older package versions
    from pythonjsonlogger import jsonlogger

    JsonFormatter = jsonlogger.JsonFormatter

from app.utils.request_context import get_request_context_dict

DEFAULT_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_MAX_BYTES = 20 * 1024 * 1024  # 20 MB
DEFAULT_BACKUP_COUNT = 10
DEFAULT_OUTPUT_MODE = "files"  # files | stdout | both

_CONFIG_LOCK = Lock()
_IS_CONFIGURED = False
_LISTENER: QueueListener | None = None


@dataclass(frozen=True)
class LoggingSettings:
    """Configuration for centralized logging."""

    service_name: str
    environment: str
    level_name: str
    log_dir: Path
    max_bytes: int
    backup_count: int
    output_mode: str

    @property
    def level(self) -> int:
        return logging.getLevelName(self.level_name.upper())  # type: ignore[return-value]

    @classmethod
    def from_env(cls) -> "LoggingSettings":
        level_name = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
        if not isinstance(logging.getLevelName(level_name), int):
            level_name = DEFAULT_LOG_LEVEL
        log_dir = Path(os.getenv("LOG_DIR", str(DEFAULT_LOG_DIR)))
        max_bytes = _read_int_env("LOG_MAX_BYTES", DEFAULT_MAX_BYTES)
        backup_count = _read_int_env("LOG_BACKUP_COUNT", DEFAULT_BACKUP_COUNT)
        output_mode = os.getenv("LOG_OUTPUT_MODE", DEFAULT_OUTPUT_MODE).lower().strip()
        if output_mode not in {"files", "stdout", "both"}:
            output_mode = DEFAULT_OUTPUT_MODE
        return cls(
            service_name=os.getenv("SERVICE_NAME", "interview_service"),
            environment=os.getenv("ENVIRONMENT", "development"),
            level_name=level_name,
            log_dir=log_dir,
            max_bytes=max_bytes,
            backup_count=backup_count,
            output_mode=output_mode,
        )


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


class StructuredJsonFormatter(JsonFormatter):
    """JSON formatter that enforces a stable schema for observability."""

    def add_fields(  # type: ignore[override]
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["message"] = log_record.get("message") or record.getMessage()
        log_record.setdefault("service", getattr(record, "service", None))
        log_record.setdefault("module", getattr(record, "module_name", record.name))
        log_record.setdefault("event", getattr(record, "event", "application_event"))
        log_record.setdefault("session_id", getattr(record, "session_id", None))
        log_record.setdefault("request_id", getattr(record, "request_id", None))
        log_record.setdefault("trace_id", getattr(record, "trace_id", None))
        log_record.setdefault("latency_ms", getattr(record, "latency_ms", None))
        log_record.setdefault("status", getattr(record, "status", None))
        log_record.setdefault("environment", getattr(record, "environment", None))
        log_record.setdefault("channel", getattr(record, "channel", "app"))
        log_record.setdefault("candidate_id", getattr(record, "candidate_id", None))
        log_record.setdefault("question_id", getattr(record, "question_id", None))
        log_record.setdefault("worker_id", getattr(record, "worker_id", None))
        log_record.setdefault("stage", getattr(record, "stage", None))
        log_record.setdefault("interview_status", getattr(record, "interview_status", None))
        log_record.setdefault("risk_score", getattr(record, "risk_score", None))
        log_record.setdefault("endpoint", getattr(record, "endpoint", None))
        log_record.setdefault("method", getattr(record, "method", None))
        if record.exc_info:
            log_record["stack_trace"] = self.formatException(record.exc_info)


class ContextEnrichmentFilter(logging.Filter):
    """Inject contextvars and defaults into all records."""

    def __init__(self, *, service_name: str, environment: str) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def filter(self, record: logging.LogRecord) -> bool:
        context = get_request_context_dict()
        record.request_id = getattr(record, "request_id", None) or context["request_id"]
        record.trace_id = getattr(record, "trace_id", None) or context["trace_id"]
        record.session_id = getattr(record, "session_id", None) or context["session_id"]
        record.service = getattr(record, "service", None) or context["service"] or self.service_name
        record.environment = getattr(record, "environment", None) or self.environment
        record.module_name = getattr(record, "module_name", None) or record.name
        record.channel = getattr(record, "channel", "app")
        return True


class ChannelFilter(logging.Filter):
    """Route records by channel to avoid duplicate file entries."""

    def __init__(self, *, allow: str | None = None, deny: str | None = None) -> None:
        super().__init__()
        self.allow = allow
        self.deny = deny

    def filter(self, record: logging.LogRecord) -> bool:
        channel = getattr(record, "channel", "app")
        if self.allow and channel != self.allow:
            return False
        if self.deny and channel == self.deny:
            return False
        return True


def configure_logging(settings: LoggingSettings | None = None) -> None:
    """Configure root logger with queue-backed rotating handlers."""
    global _IS_CONFIGURED, _LISTENER
    with _CONFIG_LOCK:
        if _IS_CONFIGURED:
            return

        resolved = settings or LoggingSettings.from_env()
        resolved.log_dir.mkdir(parents=True, exist_ok=True)

        formatter = StructuredJsonFormatter()
        context_filter = ContextEnrichmentFilter(
            service_name=resolved.service_name,
            environment=resolved.environment,
        )

        handlers: list[logging.Handler] = []
        if resolved.output_mode in {"files", "both"}:
            app_handler = _build_rotating_handler(
                resolved.log_dir / "app.log",
                level=resolved.level,
                formatter=formatter,
                filters=[context_filter, ChannelFilter(deny="audit")],
                max_bytes=resolved.max_bytes,
                backup_count=resolved.backup_count,
            )
            error_handler = _build_rotating_handler(
                resolved.log_dir / "error.log",
                level=logging.ERROR,
                formatter=formatter,
                filters=[context_filter],
                max_bytes=resolved.max_bytes,
                backup_count=resolved.backup_count,
            )
            audit_handler = _build_rotating_handler(
                resolved.log_dir / "audit.log",
                level=logging.INFO,
                formatter=formatter,
                filters=[context_filter, ChannelFilter(allow="audit")],
                max_bytes=resolved.max_bytes,
                backup_count=resolved.backup_count,
            )
            handlers.extend([app_handler, error_handler, audit_handler])

        if resolved.output_mode in {"stdout", "both"}:
            stdout_handler = logging.StreamHandler(stream=sys.stdout)
            stdout_handler.setLevel(resolved.level)
            stdout_handler.setFormatter(formatter)
            stdout_handler.addFilter(context_filter)
            handlers.append(stdout_handler)
        if not handlers:
            handlers.append(logging.NullHandler())

        log_queue: Queue[logging.LogRecord] = Queue(-1)
        queue_handler = QueueHandler(log_queue)
        queue_handler.setLevel(resolved.level)

        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(resolved.level)
        root_logger.addHandler(queue_handler)
        root_logger.propagate = False

        _LISTENER = QueueListener(log_queue, *handlers, respect_handler_level=True)
        _LISTENER.start()
        _IS_CONFIGURED = True
        atexit.register(shutdown_logging)


def shutdown_logging() -> None:
    """Stop queue listener cleanly on process shutdown."""
    global _LISTENER, _IS_CONFIGURED
    with _CONFIG_LOCK:
        if _LISTENER is not None:
            _LISTENER.stop()
            _LISTENER = None
        _IS_CONFIGURED = False


def _build_rotating_handler(
    file_path: Path,
    *,
    level: int,
    formatter: logging.Formatter,
    filters: list[logging.Filter],
    max_bytes: int,
    backup_count: int,
) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        filename=file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    for log_filter in filters:
        handler.addFilter(log_filter)
    return handler
