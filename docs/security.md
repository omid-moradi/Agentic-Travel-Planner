# Security Posture

Implemented and tested:

- **Secrets** only from env; `.env` is git-ignored and a pre-commit hook
  (`scripts/check_no_secrets.py`) blocks live credential patterns from being
  committed. `.env.example` carries placeholders only.
- **SSRF protection** on every outbound fetch: scheme/port allowlist, private/
  loopback/link-local and cloud-metadata addresses rejected *before* any
  request (`providers/http/scraper_client.py`).
- **robots.txt honoured**; a disallow raises `ScrapingNotPermittedError` and
  the registry falls down the chain. Logins, paywalls, CAPTCHAs and IP blocks
  are never bypassed; no proxy rotation or fingerprint spoofing, by design.
- **Untrusted content is sanitised**: scripts/styles/iframes/inline handlers
  stripped (JSON-LD data blocks preserved) and prompt-injection markers
  removed before any model sees page content.
- **Rate limiting** per IP (in-process; Redis-ready) and **CORS** with a
  localhost allowlist for development.
- **Auth**: PBKDF2-SHA256 (240k iterations, per-user salt, constant-time
  verify) and JWT HS256 with expiry. Password hashes never appear in logs
  (the logging layer redacts secret-shaped keys and PII patterns), and since
  the post-close hardening they live in a dedicated `user_credentials`
  table - never inside the display-safe `users.preferences` JSON. Legacy
  phase 6 hashes are verified read-only and lazily migrated on first login.
- **Payments**: test-mode adapters only, no card data is ever stored;
  webhooks are signature-checked and idempotent.
- **Agent boundaries**: the agent never books or pays (ADR-007); entry
  requirements are advisory with a mandatory warning (ADR-009).

Needs legal/business review (marked as such in the repo):

- Privacy policy and Terms of Service templates - **needs legal review**.
- GDPR-style export/delete: the data model supports it (per-user rows);
  the account screens that trigger it arrive with the auth UI work.
- Scraping any specific real site requires the robots.txt + ToS review
  recorded in `docs/data-sources.md` - owner approval required.
- Sanctions/compliance considerations for operating the Iran mode
  (documented in `docs/iran-mode.md`) - **needs legal review**.

Dependency hygiene: `pip-audit` runs in CI; pins are floors in
`pyproject.toml` and the lockfile is `package-lock.json` for the web app.
