# Deployment

## Local (zero setup)

```bash
python -m venv .venv && .venv\Scripts\activate    # Windows
pip install -e ".[dev,api]"
copy .env.example .env                            # set JWT_SECRET at minimum

# offline demo mode - no keys needed
set LLM_PROVIDER=mock
uvicorn travel_planner.api.app:app --port 8000    # API on :8000

cd web && npm ci && npm run build && npm start     # web on :3000
```

## Docker Compose (full stack)

```bash
export JWT_SECRET=<a long random string>
docker compose up --build
# api    -> http://localhost:8000
# web    -> http://localhost:3000
# postgres + redis with health checks
```

Defaults: the api boots in **offline demo mode** (`LLM_PROVIDER=mock`,
SQLite). To leave demo mode set `LLM_PROVIDER=apmix` (or `openai_compatible`
/ `ollama`), the matching key and base URL, and optionally point
`DATABASE_URL` at the Postgres service.

**Status: the Dockerfiles and compose file are committed but the build was not
executed in the development environment (the Docker daemon was not running).
See STATUS-P9.md.**

## Production checklist

- [ ] Set a real `JWT_SECRET` (>= 32 bytes; the default logs a warning).
- [ ] Move `DATABASE_URL` to Postgres (`postgresql+asyncpg://...`).
- [ ] Point `REDIS_URL` at a Redis instance (cache, rate limits).
- [ ] Tighten the CORS allowlist in `api/app.py` to your real origins.
- [ ] Set `ADMIN_BOOTSTRAP_EMAIL` before the first account creation.
- [ ] Run `alembic upgrade head` once migrations are authored (the app also
      creates its schema at startup for the zero-setup path).
- [ ] Decide the guest trial (`GUEST_TRIAL_ENABLED`) per your pricing.
- [ ] Scrapers stay disabled until each target site's robots.txt + ToS review
      is recorded in `docs/data-sources.md`.
