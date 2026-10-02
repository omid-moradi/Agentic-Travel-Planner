# Agentic Travel Planner

> **Work in progress.** Phase 0 of 10 complete. The current code is the original AutoGen
> prototype; it is being rebuilt into a modular monolith orchestrated by LangGraph.
> See [`plan-mode-cline.md`](plan-mode-cline.md) for the full phased plan and
> [`STATUS-P0.md`](STATUS-P0.md) for the current status.

An AI travel product that plans and manages an **entire trip** - for **domestic Iran trips and
international trips**, in **Persian (RTL) and English**.

---

## What it will do

**Before the trip**
- Natural-language request -> a typed `TripRequest` (asking only high-value questions).
- Destination research, day-by-day itinerary, budget breakdown, hotel and transport options.
- Packing list and document checklist.
- Entry requirements for international travel (visa, passport validity, insurance, health),
  always sourced and dated, always with a "verify with official source" warning.
- Seasonal and weather-aware planning, clearly distinguishing forecast from climate averages.

**During the trip (Live Mode)**
- Today's plan, next-stop navigation, offline-friendly cached itinerary (PWA).
- One-tap "Re-plan today" for rain, a closed venue, running late, tiredness or a budget change.
- Expense tracker with currency conversion and budget burn-down.

**After the trip**
- Trip summary, expense split between travelers, shareable public trip page, PDF/ICS export.

## Core differentiators

| Differentiator | What it means |
|---|---|
| Source-grounded facts | Every external fact is `confirmed`, `estimated`, `inferred` or `unavailable`, with a source and a retrieval time. Nothing is invented. |
| Deterministic optimization | Routes, opening hours and budgets are computed in Python from real coordinates and travel times - never guessed by the model. |
| Conversational edits | "cheaper", "remove museums", "rain on day 3", "add a day" patch only the affected parts, then revalidate. |
| Transparent agent trace | Structured steps and timings. No chain-of-thought is ever shown or stored. |

## Architecture (summary)

- **LangGraph** orchestration over a typed, checkpointed `TravelState`.
- **Provider-agnostic LLM layer** - OpenAI-compatible gateway by default, plus Ollama and an
  offline `mock` provider. No vendor lock-in.
- **Scraping-first, API-ready providers** - every capability is a `Protocol` with a configurable
  fallback chain, so an official API can replace a scraper by changing one env line.
- **FastAPI + PostgreSQL + Redis** modular monolith, with SQLite and in-process fallbacks so the
  test suite runs anywhere.
- **Next.js** web app with full RTL Persian support.

Full details: [`docs/architecture.md`](docs/architecture.md).

## Project layout

```text
docs/            audit, decisions (ADRs), architecture, data sources, reports
src/             product code (travel_planner package) - from phase 1
web/             Next.js frontend - from phase 5
evaluation/      scenario harness and metrics - from phase 8
legacy_prototype/  the original AutoGen spike - deleted in phase 4
```

## Getting started (current state)

The repository is mid-migration. For the original prototype:

```bash
pip install -r requirements.txt
cp .env.example .env     # then fill in LLM_API_KEY
python main.py           # runs the hard-coded demo task
```

Phase 1 replaces this with a proper `pyproject.toml`, a `src/` layout, and lint/type/test gates.
The exact commands for the finished product are documented in the Phase 9 README.

## Configuration

All configuration is environment-based. Copy `.env.example` to `.env` and fill it in.

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `apmix`, `openai`, `openai_compatible`, `ollama` or `mock` |
| `LLM_BASE_URL` | OpenAI-compatible endpoint |
| `LLM_API_KEY` | API key (never committed) |
| `LLM_MODEL` | Model id |
| `DATABASE_URL` | SQLAlchemy async URL; SQLite works out of the box |
| `<CAPABILITY>_PROVIDERS` | Ordered provider fallback chain per capability |
| `TAVILY_API_KEY` | Web search (optional) |

The app must run end-to-end in **demo mode with zero paid keys** (`LLM_PROVIDER=mock`).

## Development status

| Phase | Scope | Status |
|---|---|---|
| 0 | Audit, ADRs, architecture, plan | Done |
| 1 | Core foundation, apmix/LLM migration | Next |
| 2 | Agentic core + optimizer | Planned |
| 3 | Data providers (scraping-first) | Planned |
| 4 | Persistence + API | Planned |
| 5 | Web app | Planned |
| 6 | Monetization | Planned |
| 7 | Whole-trip features | Planned |
| 8 | Observability, eval, MCP | Planned |
| 9 | DevOps, docs, final report | Planned |

Honest status, including anything unverified, is recorded in each `STATUS-P<n>.md`.

## License

To be decided. All rights reserved until a license is chosen.

## Legal note

Visa and entry-requirement information is advisory only and must be verified with an official
source before travel. Scraping is performed responsibly under each site's robots.txt and recorded
in `docs/data-sources.md`. Payment and legal templates are marked "needs legal review".
