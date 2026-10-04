# Agentic Travel Planner - API image.
# Multi-stage: build the wheel in a builder, install into a slim runtime.
# The image runs the FastAPI app with uvicorn and the offline demo mode
# works out of the box (LLM_PROVIDER=mock, curated fixtures).

FROM python:3.13-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir build && python -m build --wheel --outdir /dist

FROM python:3.13-slim AS runtime

# Non-root user; the app never needs to write outside its data dir.
RUN useradd --create-home --uid 1000 planner
WORKDIR /app

COPY --from=builder /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl \
    "uvicorn[standard]" \
    "sqlalchemy[asyncio]" \
    "aiosqlite" \
    "asyncpg" \
    "email-validator" \
    "pyjwt" \
    && rm -f /tmp/*.whl

USER planner
ENV PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    LLM_PROVIDER=mock \
    DATABASE_URL=sqlite+aiosqlite:///./data/travel_planner.db

# The SQLite file lives here when the default (no-daemon) mode is used.
RUN mkdir -p /app/data
VOLUME /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4)"

CMD ["uvicorn", "travel_planner.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
