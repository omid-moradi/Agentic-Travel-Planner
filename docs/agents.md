# Agents & Orchestration

Status: implemented (phases 2-7). The graph is **LangGraph** over a typed,
checkpointed `TravelState` (ADR-002 - AutoGen was retired in phase 4).

## Graph shape

```text
START
  -> research fan-out (9 nodes, parallel)
  |    research_places, research_accommodation, research_restaurants,
  |    research_transport, research_weather, research_events,
  |    research_culture, research_safety, research_requirements
  -> plan (deterministic optimizer; the LLM is not involved)
  -> validate (code-only: structural + semantic)
       invalid & repair_count < max -> replan -> validate
       valid or budget exhausted     -> write -> END
```

## The nodes

| Node | Kind | What it does | LLM? |
|---|---|---|---|
| research_* (9) | parallel | Gather findings per capability, each with provenance (`confirmed / estimated / inferred / unavailable`) | no (fixtures; providers in phase 3) |
| plan | deterministic | Day distribution across cities, route ordering (nearest-neighbour + 2-opt), time scheduling, walk-vs-taxi legs, Toman budgeting, the 8h workload cap | **no** (ADR-008) |
| validate | deterministic | Sequence, consecutive dates, duplicate POIs, time sanity, workload cap, budget totals, requested-budget warning | no |
| replan | deterministic | Bounded repair (`repair_count < max_repair_loops`, then best-effort) | no |
| write | render | Persian or English output with confidence labels and the prices-may-differ notice | no |

## Core rules

- **No chain-of-thought ever.** The LLM layer strips `reasoning_content` at the
  client boundary; the trace stores structured steps only.
- **No node overwrites another's work** - nodes append to list fields on the state.
- **The trace is data, not prose**: `AgentRun{node, status, tokens, duration_ms, payload}`.
- **Honesty**: unavailable data is labelled unavailable (ADR-009); validation
  warnings are persisted as messages so they are always visible.

## Where the LLM fits

The deterministic pipeline produces the plan. The LLM is used for narrative and
intent work (selection/wording) and is provider-agnostic
(`apmix | openai | openai_compatible | ollama | mock`). In offline demo mode
(`LLM_PROVIDER=mock`) the whole graph runs with zero network calls.
