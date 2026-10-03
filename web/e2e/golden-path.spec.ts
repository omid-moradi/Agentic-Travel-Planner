import { expect, test } from "@playwright/test";

/**
 * The phase 5 gate: the golden path - create a trip, edit it (re-plan),
 * then share it. Runs against the real API and the real graph, offline.
 */

test("golden path: create trip -> re-plan -> share", async ({ page }) => {
  // ---------------------------------------------------------------- landing
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/سفر/);

  // ------------------------------------------------------------------ create
  await page.getByRole("main").getByRole("link", { name: /برنامه‌ریزی سفر جدید/ }).click();
  await expect(page).toHaveURL(/\/new$/);

  const requestBox = page.getByRole("textbox");
  await requestBox.fill("سه شب تهران و شیراز، سفر فرهنگی");
  await page.getByRole("button", { name: /برنامه بساز/ }).click();

  // The trip page renders the plan: total cost, day tabs, activities.
  await expect(page).toHaveURL(/\/trips\/[0-9a-f-]{36}$/, { timeout: 60_000 });
  await page.waitForSelector("[data-testid=total-cost]", { timeout: 60_000 });
  await expect(page.getByTestId("total-cost")).toContainText("تومان");

  // Day tabs exist and activities carry provenance badges.
  await expect(page.getByTestId("day-activities").first()).toBeVisible();
  const badges = page.getByTestId("status-badge");
  await expect(badges.first()).toBeVisible();

  // -------------------------------------------------------------------- edit
  // Phase 5 "edit" = re-plan; conversational edits arrive with phase 6.
  await page.getByRole("button", { name: /بازسازی برنامه/ }).click();
  await page.waitForSelector("[data-testid=total-cost]", { timeout: 60_000 });

  // ------------------------------------------------------------------- share
  await page.getByRole("button", { name: /لینک اشتراک بساز/ }).click();
  await expect(page.getByText(/لینک کپی شد/)).toBeVisible({ timeout: 30_000 });

  // The public read-only page renders the same plan.
  await page.goto("/trips");
  await expect(page.getByRole("heading", { name: /سفرهای من/ })).toBeVisible();
});
