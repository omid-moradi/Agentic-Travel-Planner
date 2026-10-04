# Iran Mode

`RegionProfile` (config-driven) selects providers, currency, calendar and
language per trip. Iran mode specifics implemented today:

| Concern | Implementation |
|---|---|
| Calendar | Jalali (Shamsi) profile field; the API stores ISO dates and the profile declares the display calendar (the Jalali renderer lands with the web date work) |
| Language | Persian (fa) primary with full RTL in the web app, Persian digits in the fa locale |
| Currency | Toman by default with an IRR toggle (`Toman = IRR / 10`), always labelled in words to prevent the classic Toman/Rial confusion |
| Maps/routing | OSM-based stack (Nominatim/OSRM, self-hostable); Neshan/Balad adapter slots behind env keys |
| Local context | Modest-dress checklist items, cash-for-ride-apps guidance, Nowruz peak season in the evaluation scenarios, prayer/closing-time awareness in the planner prompts |
| Connectivity | The core runs offline (`LLM_PROVIDER=mock`) or through a configurable gateway (`apmix`, any OpenAI-compatible endpoint, local Ollama) - nothing hard-depends on a Western API |

Sanctions/compliance considerations for operating Iran mode are **flagged for
legal review** - see the open questions in `docs/security.md`.
