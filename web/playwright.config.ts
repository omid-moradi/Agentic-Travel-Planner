import { defineConfig } from "@playwright/test";

/**
 * The golden-path config: the API server and the web server are started by
 * Playwright itself (webServer entries), so one command runs the whole stack.
 */

// Cross-platform interpreter (overridable), used for both server boot steps.
const py = process.env.API_PYTHON ?? "python";

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  retries: 0,
  workers: 1,
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      // `python` on PATH works on Windows dev and Linux CI alike. The e2e
      // SQLite file lives in ./.pytest_tmp which does NOT exist on a fresh
      // checkout (the pytest fixtures create it, but nothing does for e2e),
      // and the API exits at startup when the parent dir is missing - so the
      // dir is created here, cross-platform, before uvicorn boots.
      command:
        `${py} -c "import pathlib; pathlib.Path('.pytest_tmp').mkdir(exist_ok=True)"` +
        ` && ${py} -m uvicorn travel_planner.api.app:app --port 8000`,
      cwd: "..",
      url: "http://localhost:8000/api/v1/health",
      reuseExistingServer: true,
      timeout: 60_000,
      env: {
        PYTHONPATH: "src",
        LLM_PROVIDER: "mock",
        // The golden path creates several trips; the guest trial (one plan)
        // would block re-runs on the persistent e2e database. Quotas have
        // their own dedicated tests in test_monetization.py.
        GUEST_TRIAL_ENABLED: "false",
        DATABASE_URL: "sqlite+aiosqlite:///./.pytest_tmp/e2e_golden.db",
      },
    },
    {
      command: "npm run start",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
