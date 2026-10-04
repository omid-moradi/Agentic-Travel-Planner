# API Reference

Base URL: `/api/v1`. Every response carries an `X-Request-ID` header; every
error is the envelope `{"error": {"code", "message", "request_id", "details"}}`.
Rate limiting: in-process per-IP (Redis drops in behind the same interface).

## Health

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/ready` | readiness + config summary |
| GET | `/metrics` | Prometheus text format |

## Trips

| Method | Path | Notes |
|---|---|---|
| POST | `/trips` | create + plan inline. Body: `request` (required, 3-4000 chars), `region` (iran/international), `language` (fa/en), `start_date`, `duration_nights`, `travelers`, `budget_total`. Quota-checked: guests get 1 plan (guest trial); 402 `quota_exceeded` when the limit is hit. |
| GET | `/trips` | list |
| GET | `/trips/{id}` | detail |
| GET | `/trips/{id}/itinerary` | latest version + full payload |
| GET | `/trips/{id}/messages` | conversation history |
| GET | `/trips/{id}/trace` | agent trace (structured steps, never chain-of-thought) |
| POST | `/trips/{id}/replan` | new itinerary version; history kept |
| GET | `/trips/{id}/checklist` | packing list + document checklist |
| GET | `/trips/{id}/entry-requirements` | advisory entry rules with the mandatory warning |
| POST | `/trips/{id}/expenses` | record an expense (converted at insert time) |
| GET | `/trips/{id}/expenses` | items + burn-down (spent/budget/remaining) |
| GET | `/trips/{id}/export.ics` | RFC 5545 calendar download |
| GET | `/trips/{id}/export.pdf` | one-page PDF download |
| GET | `/trips/{id}/today` | Live Mode: today's plan + next-stop + re-plan reasons |
| POST | `/trips/{id}/replan-today` | reason-aware, day-scoped re-plan: `{"reason": "rain|closed_venue|running_late|tired|budget_changed"}`. The deterministic planner re-runs, then only **today's day** carries the reason patch (lighter day, no walking legs in the rain, a cheaper day, ...); every other day keeps the plan the traveller already has. The reason and the `day_patched` flag are recorded on the trace. When today is not a trip day the fresh full plan is stored unchanged. |
| POST | `/trips/{id}/share` | create (idempotent) a share token |

## Share (public, read-only)

| Method | Path | Notes |
|---|---|---|
| GET | `/share/{token}` | the public trip view; no edit actions exist |

## Auth

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | email + password (min 8 chars); returns a JWT |
| POST | `/auth/login` | returns a JWT |
| GET | `/auth/me` | bearer token required |

## Billing

| Method | Path | Notes |
|---|---|---|
| POST | `/billing/checkout` | behind `BILLING_ENABLED`; test-mode providers only |
| GET | `/billing/status` | plan, subscription status, quota limits |
| POST | `/billing/webhook` | idempotent by `(provider, event_id)`; duplicate -> `{"duplicate": true}` with 200 |

## Admin

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/stats` | admin role required; users/trips/plans/tokens |

## Affiliate

| Method | Path | Notes |
|---|---|---|
| POST | `/affiliate/click` | records the click and returns the redirect URL + mandatory commission disclosure (ADR-007) |
