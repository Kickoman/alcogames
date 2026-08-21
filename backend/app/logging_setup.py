"""Structured JSON logging for the service.

Every event is one JSON line on stdout, matching the schema the log
aggregator expects. Nothing is shipped from here -- the collector reads
stdout, so the service stays unaware of where logs end up.

Two streams are produced:

``http_request``
    One event per request: method, route, status, duration.
``internal``
    Anything the handlers choose to record, via ``get_logger()``.

Note on secrets: request headers are never logged, which is what keeps
``X-Admin-Token`` out of the log store. Keep it that way.
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.routing import Mount

# Set per request, picked up by every log line emitted while handling it --
# including logs from libraries that know nothing about this module.
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")

# Routes logged at debug level, i.e. dropped at the default level.
QUIET_ROUTES = frozenset({"/api/health"})


def _add_context(_logger: Any, _name: str, event: dict) -> dict:
    event.setdefault("service", os.environ.get("SERVICE_NAME", "alcogames"))
    event.setdefault("stream", "internal")
    if trace_id := _trace_id.get():
        event.setdefault("trace_id", trace_id)
    return event


def _rename_fields(_logger: Any, _name: str, event: dict) -> dict:
    # structlog names them "timestamp" and "event"; the schema wants "ts",
    # and separates the machine-readable event name from the human message.
    event["ts"] = event.pop("timestamp")
    event.setdefault("message", event.get("event", ""))
    return event


_SHARED_PROCESSORS = [
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    _add_context,
]


def setup_logging(service: str = "alcogames", level: str | None = None) -> None:
    os.environ.setdefault("SERVICE_NAME", service)
    level = (level or os.environ.get("LOG_LEVEL", "info")).upper()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            *_SHARED_PROCESSORS,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _rename_fields,
            # ensure_ascii=False: content here is largely Russian, and escaped
            # \uXXXX makes logs unreadable and needlessly larger.
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route uvicorn's own logs through the same renderer, so the collector
    # never has to deal with two formats on one stream.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(ensure_ascii=False),
            foreign_pre_chain=[*_SHARED_PROCESSORS, _rename_fields],
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level))

    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True

    # uvicorn.access repeats what RequestLogMiddleware already records, only
    # unstructured. Silence it rather than store every request twice.
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False
    access.disabled = True


def get_logger(stream: str = "internal", **bound: Any):
    """Return a lazily-configured logger.

    Values are passed to ``get_logger`` rather than ``.bind()`` on purpose:
    ``.bind()`` resolves the configuration immediately, so a module-level
    ``log = get_logger()`` in a router would freeze the default console
    renderer -- routers are imported before ``setup_logging()`` runs, and
    their events would come out unstructured while everything else is JSON.
    """
    return structlog.get_logger(stream=stream, **bound)


def new_trace(trace_id: str | None = None) -> str:
    trace_id = trace_id or uuid.uuid4().hex
    _trace_id.set(trace_id)
    return trace_id


def _route_of(request: Request) -> str:
    """Route pattern, not the raw path.

    ``/games/{game_id}`` keeps the endpoint countable; the raw path would
    make every game id its own endpoint and blow up cardinality.

    The static frontend is a Mount at "/", so its ``path`` is "/" for every
    asset. That would lump index.html together with every css and js file,
    so for mounts the real path is used instead -- the set of static files
    is small and fixed, so cardinality stays bounded.
    """
    route = request.scope.get("route")
    if route is None:
        return request.url.path
    if isinstance(route, Mount):
        return request.url.path
    return getattr(route, "path", None) or request.url.path


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Emits one ``http_request`` event per request."""

    def __init__(self, app):
        super().__init__(app)
        self._log = get_logger(stream="http_request")

    async def dispatch(self, request: Request, call_next):
        # Reuse the caller's trace id when present, so one id spans services.
        trace_id = new_trace(request.headers.get("x-trace-id"))
        started = time.perf_counter()
        status, error = 500, ""

        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["x-trace-id"] = trace_id
            return response
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            route = _route_of(request)
            if status >= 500:
                level = "error"
            elif route in QUIET_ROUTES:
                level = "debug"
            else:
                level = "info"

            getattr(self._log, level)(
                "http_request",
                http_method=request.method,
                http_path=route,
                http_status=status,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error=error,
                client=request.headers.get(
                    "x-forwarded-for", request.client.host if request.client else ""
                ),
            )
