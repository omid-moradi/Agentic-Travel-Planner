# Monetization

Implemented (phase 6, all test-covered):

| Feature | How |
|---|---|
| Guest trial | Anonymous callers get **1 free plan** (the master prompt's trial); the second request returns `402 quota_exceeded` with plan/limit/used details. Disable with `GUEST_TRIAL_ENABLED=false`. |
| Accounts | Email + password (PBKDF2), JWT, roles; `ADMIN_BOOTSTRAP_EMAIL` grants the admin role to the first matching account. |
| Plans & quotas | `EntitlementService`: guest / free / pro / team with monthly plan and re-plan limits and token caps, metered from `usage_events`. Quotas are shown at `GET /billing/status` and enforced on `POST /trips`. |
| Payments | `PaymentProvider` protocol with **Mock** (default), **Stripe** and **Zarinpal** adapters - disabled stubs without credentials, test mode only, no card data. A subscription state machine (`incomplete -> active -> past_due -> canceled`) refuses illegal transitions. |
| Webhooks | Idempotent by `(provider, event_id)` with a unique constraint; duplicates return 200 + `duplicate: true`; forged signatures get 401. |
| Affiliate | `POST /affiliate/click` records the click, appends the env-sourced id, and returns a mandatory commission disclosure. **The agent never books or pays** - redirect only (ADR-007). |
| Admin | `GET /admin/stats`: users, trips, plans, valid itineraries, tokens - 401 anonymous / 403 regular / 200 admin. |

Business items that remain (recorded honestly):

- Real Stripe / Zarinpal onboarding and their live signature schemes.
- Referral credits, OG share images, the "plan a similar trip" CTA.
- A cost-per-plan dashboard once live token counts flow (the accounting and
  the metrics endpoint exist; the offline graph records 0 tokens by design).
- Pricing page copy and the payment provider choice per market - business
  decisions, not code.
