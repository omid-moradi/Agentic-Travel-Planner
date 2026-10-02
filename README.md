# Agentic Travel Planner

> **Work in progress.** Phases 0 and 1 of 10 are complete. The product core (schemas, the
> LangGraph workflow, the optimizer and the data providers) is not written yet - what exists
> today is the foundation: typed configuration, a provider-agnostic model layer, structured
> logging, a CLI and a test suite. See [`plan-mode-cline.md`](plan-mode-cline.md) for the plan,
> [`STATUS-P0.md`](STATUS-P0.md) and [`STATUS-P1.md`](STATUS-P1.md) for honest status.

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

- **LangGraph** orchestration over a typed, checkpointed `TravelState` (phase 2).
- **Provider-agnostic LLM layer** - any OpenAI-compatible endpoint, plus Ollama and an
  offline `mock` provider. No vendor lock-in.
- **Scraping-first, API-ready providers** - every capability is a `Protocol` with a
  configurable fallback chain, so an official API can replace a scraper by changing one env
  line (phase 3).
- **FastAPI + PostgreSQL + Redis** modular monolith, with SQLite and in-process fallbacks so
  the test suite runs anywhere (phase 4).
- **Next.js** web app with full RTL Persian support (phase 5).

Full details: [`docs/architecture.md`](docs/architecture.md).

## Getting started

### Requirements

Python 3.11+ (developed and tested on 3.13.5).

### Install

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows
pip install -e ".[dev]"
```

### Configure

```bash
copy .env.example .env                # Windows
cp .env.example .env                  # macOS / Linux
```

Then set at least:

```dotenv
LLM_PROVIDER=apmix
LLM_BASE_URL=https://api.apmix.ai/v1
LLM_API_KEY=your_key_here
LLM_MODEL=deepseek/deepseek-v4-flash-free
```

`.env` is git-ignored and a pre-commit hook blocks live credentials from being committed.

To run completely offline with no keys at all, set `LLM_PROVIDER=mock`.

### Use the CLI

```bash
travel-planner config      # effective configuration, secrets masked
travel-planner ping "What is the best time to visit Kashgar?"
travel-planner --help
```

### Run the checks

```bash
ruff check src tests scripts   # lint
mypy                           # strict type check
pytest -q                      # offline suite (66 tests)
pytest -m live                 # opt-in tests that call the real gateway (7 tests)
pytest -q --cov                # with coverage (currently 88%)
pre-commit run --all-files     # all of the above plus secret scanning
```

### Layout

```text
src/travel_planner/
  errors.py            shared exception hierarchy
  config/settings.py   typed env settings, no import-time validation
  config/regions.py    Iran / international market profiles
  llm/factory.py       provider-agnostic model layer
  logging_config.py    structured logs with secret and PII redaction
  cli.py               command line entry point
docs/                  audit, decisions (ADRs), architecture, data sources, reports
tests/unit             offline tests
tests/integration      opt-in live provider tests
evaluation/            scenario harness (phase 8)
legacy_prototype/      the original AutoGen spike, deleted in phase 4
```

## Development status

| Phase | Scope | Status |
|---|---|---|
| 0 | Audit, ADRs, architecture, plan | **Done** |
| 1 | Core foundation, LLM migration, quality gates | **Done** |
| 2 | Agentic core + optimizer | Next |
| 3 | Data providers (scraping-first) | Planned |
| 4 | Persistence + API | Planned |
| 5 | Web app | Planned |
| 6 | Monetization | Planned |
| 7 | Whole-trip features | Planned |
| 8 | Observability, eval, MCP | Planned |
| 9 | DevOps, docs, final report | Planned |

Honest status, including anything unverified, is recorded in each `STATUS-P<n>.md`.

## Known limitations right now

- **There is no trip planning yet.** No `TripRequest`, no itinerary, no graph. Phases 2+.
- **No data providers yet.** No places, hotels, weather or routes. Phase 3.
- **No API, database or web app yet.** Phases 4 and 5.
- Docker, PostgreSQL and Redis were unavailable in the development environment, so those
  parts are planned but unbuilt.

## License

To be decided. All rights reserved until a license is chosen.

## Legal note

Visa and entry-requirement information is advisory only and must be verified with an official
source before travel. Scraping is performed responsibly under each site's robots.txt and recorded
in `docs/data-sources.md`. Payment and legal templates are marked "needs legal review".
