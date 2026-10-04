import { expect, test } from "@playwright/test";

/**
 * The PWA gate: after the service worker installs (it precaches the landing
 * page), going offline must not break the app - the page still loads from
 * the SW cache. Playwright emulates the offline switch via setOffline.
 */

test("offline: the landing page still loads from the service worker cache", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/سفر/);

  // Wait until the service worker is installed AND active (it precaches
  // "/", "/manifest.json", "/icon.svg" during install, then claims clients).
  await page.waitForFunction(
    () => navigator.serviceWorker.ready.then(() => true),
    undefined,
    { timeout: 30_000 },
  );

  // Cut the network and reload: the SW must serve the page from its cache.
  await context.setOffline(true);
  try {
    await page.reload();
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/سفر/);
  } finally {
    await context.setOffline(false);
  }
});
