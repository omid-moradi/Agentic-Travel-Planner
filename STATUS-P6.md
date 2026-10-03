# STATUS - Phase 6 (Monetization)

Date: 2026-10-03
Branch: `phase/6-monetization`
Gate: webhook + entitlement tests green. **Passed.**

---

## Done

- [x] **Auth** (`services/auth.py`, `routers/auth.py`): email registration and
      login, PBKDF2-SHA256 password hashing (240k iterations, per-user salt,
      constant-time verify), JWT HS256 access tokens via PyJWT with expiry,
      roles (user/admin), the master prompt's **guest trial** (one free plan
      without signup), and a bootstrap admin via ``ADMIN_BOOTSTRAP_EMAIL``.
      Endpoints: ``POST /auth/register``, ``POST /auth/login``, ``GET /auth/me``.
- [x] **EntitlementService** (`services/entitlements.py`): plan tiers
      guest/free/pro/team with monthly quotas (plans, replans, token caps),
      usage metered from the existing ``usage_events`` table, and a
      ``QuotaExceededError`` that surfaces as the ``402 quota_exceeded``
      envelope with plan/limit/used details. Wired into ``POST /trips``.
      ``GUEST_TRIAL_ENABLED=false`` treats anonymous callers like the free
      tier (a deployment switch; used by the phase 4 API tests).
- [x] **Payments** (`services/payments.py`, `routers/billing.py`):
      ``PaymentProvider`` protocol; **Mock** (default, offline), **Stripe**
      (disabled without key), **Zarinpal** (behind the flag, disabled without
      merchant id). A subscription **state machine** with legal transitions
      only (incomplete -> active -> past_due -> canceled), and an
      **idempotent webhook**: ``webhook_events`` has a unique
      (provider, event_id) constraint and duplicates are no-ops that still
      return 200. Signature verification rejects unknown signatures with 401.
      Endpoints: ``POST /billing/checkout``, ``GET /billing/status``,
      ``POST /billing/webhook``.
- [x] **Affiliate links** (`services/affiliate.py`, `routers/affiliate.py`):
      redirect only, env-sourced affiliate ids, click tracking into
      ``affiliate_clicks``, and a mandatory commission disclosure in the
      response. The agent never books or pays (ADR-007).
      Endpoint: ``POST /affiliate/click``.
- [x] **Admin** (`routers/admin.py`): ``GET /admin/stats`` (users, trips,
      plans, valid itineraries, tokens) protected by the admin role - 401 for
      anonymous, 403 for regular accounts.
- [x] New settings: ``JWT_SECRET``, ``ACCESS_TOKEN_EXPIRY_MINUTES``,
      ``ADMIN_BOOTSTRAP_EMAIL``; new table ``webhook_events``;
      ``.env.example`` and ``pyproject.toml`` updated.

## Verified (actually executed)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check src tests scripts` | **All checks passed** |
| Types | `mypy` (strict, 60 files) | **Success: no issues found** |
| **Gate: monetization tests** | `pytest tests/integration/test_monetization.py` | **15 passed** |
| Full offline suite | `pytest -m "not live"` | **179 passed** |
| Phase 5 golden path | `npx playwright test` | **1 passed** (with the new quota logic in place) |

What the gate tests actually prove:

- a guest gets **exactly one** plan, the second request is ``402`` with the
  quota envelope (guest trial);
- a registered free account reaches its monthly limit and is refused;
- a webhook **activates** a subscription exactly once, and a **duplicate
  delivery is a no-op** that still returns 200 (idempotency);
- a **forged signature is rejected** with 401;
- the state machine **refuses illegal transitions** (active->active,
  canceled->active);
- affiliate clicks record with a commission disclosure;
- admin stats: 401 anonymous, 403 regular, 200 for the bootstrap admin.

## Implemented but NOT verified

| Item | Why | How to verify |
|---|---|---|
| Stripe / Zarinpal live calls | no credentials exist; both adapters are disabled stubs by design | set STRIPE_SECRET_KEY (test mode) or ZARINPAL_MERCHANT_ID (sandbox) and run a checkout + webhook round trip |
| Real Stripe signature scheme | requires the webhook secret; the stub rejects without it | implement the HMAC scheme when onboarding |
| OAuth (Google) | scheduled with the account screens; email auth is complete | phase 6.1 |
| Referral credits, OG images, "plan a similar trip" CTA | the share page exists; the viral loop mechanics are next | phase 6.1/7 |
| Cost-per-plan token accounting | usage events are recorded with tokens=0 until the graph reports LLM usage | phase 8 (observability) wires real token counts |

## Known limitations (honest)

- Password hashes live in the user's preferences JSON under a reserved key -
  a dedicated credential table arrives with the OAuth work; the hash function
  itself is production-grade PBKDF2.
- Tokens are opaque JWTs without refresh tokens or revocation; the short
  default expiry (24h) is the mitigation until a refresh flow exists.
- The admin dashboard is currently a stats endpoint; the UI arrives with the
  admin screens in phase 6.1.
- Quota counting joins usage events through trips; usage rows with no trip
  (e.g. affiliate clicks) do not count toward plan quotas, which matches the
  product intent.

## Decisions taken

- **Subscriptions start as ``incomplete``** so the first
  ``subscription.created`` webhook is a legal transition - creating them
  ``active`` made the first event an error (found by the gate tests).
- **Duplicate webhooks return 200 with ``duplicate: true``** - providers
  retry until they see success and must not be punished for our bug.
- **The phase 4 API tests raise their quota via env** rather than mocking the
  entitlement service: quota behaviour keeps its own dedicated tests with
  fresh databases.

## Next - Phase 7 (Whole-trip features)

1. Entry requirements (international) - sourced, dated, always with the
   "verify with official source" warning.
2. Packing list + document checklist.
3. Live Mode PWA: today's plan, offline cache, one-tap re-plan.
4. Expense tracker with currency conversion and budget burn-down.
5. ICS + PDF export.
6. Gate: export tests green; Live Mode replan covered by unit tests.
