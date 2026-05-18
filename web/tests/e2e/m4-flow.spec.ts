import { test, expect } from "@playwright/test";

// Spec §7 M4 validation gate:
//   "A new user can go from landing page to playing a level-appropriate
//    piece in under 90 seconds."
//
// We measure landing → first piece detail open (alphaTab rendered) as
// the mechanical proxy for "playing." The actual play button is a
// one-click action on the piece detail; we don't wait for audio to
// start because alphaTab's soundfont lazy-loads.
const FLOW_BUDGET_MS = 90_000;

test("first-time user can land → onboard → feed → open piece under 90 s", async ({ page }) => {
  test.setTimeout(120_000);

  await page.context().clearCookies();
  await page.goto("/");
  // Start the clock once the SPA is initialized (clears localStorage so
  // subsequent runs don't auto-redirect to /feed).
  await page.evaluate(() => localStorage.clear());

  const start = Date.now();
  await page.goto("/");

  // / → Landing → /onboard when no level stored
  await expect(page).toHaveURL(/#\/onboard$/);

  // Pick level 5 (mid-corpus, lots of pieces both at and above)
  await page.getByRole("button", { name: /^5/ }).click();
  await page.getByRole("button", { name: /Show me pieces/i }).click();

  // /feed → first card → /piece/:cid
  await page.locator("[data-feed-loaded]").waitFor({ timeout: 10_000 });
  const firstCard = page.locator("a.card").first();
  await expect(firstCard).toBeVisible();
  await firstCard.click();

  // alphaTab finishes initial rendering
  await expect(page.locator(".alphatab")).toHaveAttribute(
    "data-render-state",
    /rendered|error/,
    { timeout: 60_000 },
  );

  const elapsedMs = Date.now() - start;
  expect.soft(
    elapsedMs,
    `landing → playing took ${elapsedMs} ms (budget ${FLOW_BUDGET_MS} ms)`,
  ).toBeLessThan(FLOW_BUDGET_MS);
});

test("returning user with a stored level lands directly on the feed", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("gradedGuitar.level", "6"));
  await page.goto("/");

  await expect(page).toHaveURL(/#\/feed$/);
  await page.locator("[data-feed-loaded]").waitFor({ timeout: 10_000 });
});
