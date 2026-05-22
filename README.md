# Centralized-Logging-System

Production-oriented centralized logging framework for a distributed FastAPI backend.

## Implemented architecture

```text
FastAPI Application
  -> RequestLoggingMiddleware
  -> Structured JSON Logger (QueueHandler)
  -> QueueListener (background thread)
  -> Rotating handlers: app.log / error.log / audit.log
  -> Future sink integrations (ELK/Loki/Otel-ready schema)
```

## Folder structure

```text
backend/
├── app/
│   ├── core/
│   │   ├── exception_handlers.py
│   │   ├── logger.py
│   │   └── logging_config.py
│   ├── integration/
│   │   ├── contracts.py
│   │   ├── correlation_headers.py
│   │   └── http_client.py
│   ├── middleware/
│   │   └── request_logging.py
│   ├── tracing/
│   │   └── event_tracer.py
│   ├── utils/
│   │   └── request_context.py
│   ├── logs/
│   │   └── .gitkeep
│   └── main.py
└── requirements.txt
```

## Key capabilities

- Structured JSON logs with fixed observability schema
- Correlation IDs (`request_id`, `trace_id`, `session_id`) via `contextvars`
- Async-safe logging via `QueueHandler` + `QueueListener`
- Cross-service correlation header propagation helpers (`X-Request-ID`, `X-Trace-ID`, `X-Session-ID`)
- Interview lifecycle constants aligned with orchestration/session modules
- Rotating log aggregation:
  - `app.log` (application + request logs)
  - `error.log` (error and exception logs)
  - `audit.log` (audit channel events)
- Docker/multi-worker compatibility with stdout mode (`LOG_OUTPUT_MODE=stdout`)
- FastAPI middleware for request metrics and exception-aware request logs
- Global FastAPI exception handlers with centralized error logging
- Event tracing utility for start/completed/failed lifecycle stages

## Internship ecosystem alignment (validated)

Reviewed references:

- `system_integration` (FastAPI orchestrator endpoints and session/proctor event patterns)
- `API_ARCHITECT` (standard request/response payload structure)
- `Task1-Distributed-AI-Interview-Orchestration-Multi-Node-Execution-Framework` (session states and stage flow)
- `-System-Monitoring-Logging-Deployment-Stability-Framework-` (monitoring/logging baseline)
- `logging-debug-monitoring` (structured logging baseline)
- `AI-Interview-Testing` + Phase 5 task spec docs (Task 16 acceptance expectations)

Implemented compatibility points:

- Handles both numeric and string-like `session_id` patterns.
- Emits lifecycle statuses compatible with distributed orchestrator states (`CREATED`, `QUEUED`, `PROCESSING`, `COMPLETED`, etc.).
- Supports stage events matching worker flow (`video_analysis`, `audio_analysis`, `evaluation`, `risk_scoring`).
- Adds correlation header propagation utilities for internal service-to-service calls.
- Supports high-volume container deployment via stdout JSON logs (collector-ready).

## Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Environment variables

- `SERVICE_NAME` default: `interview_service`
- `ENVIRONMENT` default: `development`
- `LOG_LEVEL` default: `INFO`
- `LOG_DIR` default: `backend/app/logs`
- `LOG_MAX_BYTES` default: `20971520` (20MB)
- `LOG_BACKUP_COUNT` default: `10`
- `LOG_OUTPUT_MODE` default: `files` (`files` | `stdout` | `both`)
