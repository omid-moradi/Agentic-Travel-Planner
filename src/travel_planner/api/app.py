"""FastAPI application - `/api/v1`, async, typed, with one error envelope.

Conventions (master prompt section 6):

* every response carries a ``X-Request-ID`` header; the same id appears in
  the error envelope and the structured logs,
* every error is the envelope ``{"error": {"code", "message", "request_id", "details"}}``,
* rate limiting is in-process in this phase (Redis drops in behind the same
  interface in production),
* the graph runs synchronously inside the request in this phase; background
  workers + SSE arrive with the queue in a later phase, behind these same routes.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from travel_planner.db.session import create_all, resolve_database_url

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


class InProcessRateLimiter:
    """Fixed-window per-IP limiter. Redis replaces this in production."""

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, tuple[float, int]] = {}

    def check(self, key: str) -> bool:
        """True when the request is allowed."""
        now = time.monotonic()
        window_start, count = self._hits.get(key, (now, 0))
        if now - window_start >= self._window:
            window_start, count = now, 0
        allowed = count < self._max
        self._hits[key] = (window_start, count + 1)
        return allowed


def error_response(status: int, code: str, message: str, request_id: str, details: object = None) -> JSONResponse:
    """The single error envelope used everywhere."""
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "details": details,
            }
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the schema on startup (Alembic owns it in production).

    Uses the app's own ``state.database_url`` so a test app pointed at a
    throwaway database never touches the default one.
    """
    database_url = str(app.state.database_url or resolve_database_url())
    app.state.database_url = database_url
    await create_all(database_url)
    logger.info("database ready: %s", database_url.split("@")[-1])
    yield


def create_app(*, database_url: str | None = None, rate_limit: int = 60) -> FastAPI:
    """Build the FastAPI application with all routers attached."""
    from fastapi.middleware.cors import CORSMiddleware

    from travel_planner.api.routers import health, share, trips, usage

    app = FastAPI(
        title="Agentic Travel Planner API",
        version="0.1.0",
        description=(
            "Plans and manages entire trips - domestic Iran and international - "
            "in Persian (RTL) and English."
        ),
        lifespan=lifespan,
    )
    app.state.database_url = database_url or resolve_database_url()
    app.state.rate_limiter = InProcessRateLimiter(max_requests=rate_limit)

    # CORS: localhost origins for development; tighten via env in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def rate_limit_and_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        client = request.client.host if request.client else "unknown"
        if not request.app.state.rate_limiter.check(client):
            return error_response(
                429, "rate_limited", "Too many requests; slow down.", request_id
            )
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    app.include_router(trips.router, prefix=API_PREFIX)
    app.include_router(usage.router, prefix=API_PREFIX)
    app.include_router(share.router, prefix=API_PREFIX)
    app.include_router(health.router, prefix=API_PREFIX)
    return app


app = create_app()

