import { test, expect } from "@playwright/test";

// Spec §7 M5 validation gates this covers:
//   - Status changes persist across sessions.
//   - Marking pieces 'too hard' measurably changes the next feed load.
//   - Account deletion actually deletes (verified by inspecting localStorage).
//
// Identity gates (sign up / sign in / sign out) are intentionally not
// covered — there is no real auth at M5 by design
// (decisions/0012-m5-local-accounts.md).

async function seedProfile(page, level = 5) {
  await page.goto("/");
  await page.evaluate((lvl) => {
    localStorage.clear();
    const id = "p_e2e";
    localStorage.setItem(
      "gradedGuitar.profiles",
      JSON.stringify([
        { id, display_name: "E2E", created_at: "2026-01-01T00:00:00Z", level: lvl },
      ]),
    );
    localStorage.setItem("gradedGuitar.activeProfileId", id);
  }, level);
}

test("status mark persists across reload and appears in library", async ({ page }) => {
  await seedProfile(page);
  await page.goto("/#/feed");
  await page.locator("[data-feed-loaded]").waitFor({ timeout: 10_000 });

  // Open the first piece and mark it as "playing"
  const firstCard = page.locator("a.card").first();
  const firstHref = await firstCard.getAttribute("href");
  await firstCard.click();
  await page.locator(".alphatab").waitFor({ timeout: 30_000 });
  await page.getByRole("button", { name: /^Playing$/ }).click();

  // Reload — the active state must survive
  await page.reload();
  await page.locator(".alphatab").waitFor({ timeout: 30_000 });
  await expect(page.getByRole("button", { name: /^Playing$/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  // Library shows it under the Playing tab
  await page.goto("/#/library");
  await page.locator("[data-library-loaded]").waitFor({ timeout: 10_000 });
  await expect(page.locator(".row").first()).toBeVisible();
  // The first card's href encodes the cid; the library row should link
  // to the same destination.
  await expect(page.locator(`a.row[href="${firstHref}"]`)).toHaveCount(1);
});

test("'too hard' on a piece removes it from the feed on next load", async ({ page }) => {
  await seedProfile(page);
  await page.goto("/#/feed");
  await page.locator("[data-feed-loaded]").waitFor({ timeout: 10_000 });

  const targetCard = page.locator("a.card").first();
  const targetHref = await targetCard.getAttribute("href");
  await targetCard.click();
  await page.locator(".alphatab").waitFor({ timeout: 30_000 });
  await page.getByRole("button", { name: /Too hard/i }).click();

  // Reload the feed — the piece should be gone
  await page.goto("/#/feed");
  await page.locator("[data-feed-loaded]").waitFor({ timeout: 10_000 });
  await expect(page.locator(`a.card[href="${targetHref}"]`)).toHaveCount(0);
});

test("deleting a profile clears its stored data", async ({ page }) => {
  await seedProfile(page);
  await page.goto("/#/feed");
  await page.locator("[data-feed-loaded]").waitFor({ timeout: 10_000 });
  await page.locator("a.card").first().click();
  await page.locator(".alphatab").waitFor({ timeout: 30_000 });
  await page.getByRole("button", { name: /^Playing$/ }).click();

  // Status record should exist
  const before = await page.evaluate(() =>
    localStorage.getItem("gradedGuitar.status.p_e2e"),
  );
  expect(before).not.toBeNull();

  // Auto-accept the confirm() prompt and delete the profile
  page.once("dialog", (d) => d.accept());
  await page.goto("/#/profile");
  await page.getByRole("button", { name: /^Delete$/ }).first().click();

  // Note: listProfiles() seeds a fresh default profile whenever the
  // list is empty — that's intentional so the app always has a
  // working profile. We assert the *specific* deleted profile is
  // gone, not that the list is empty.
  const after = await page.evaluate(() => ({
    profiles: localStorage.getItem("gradedGuitar.profiles"),
    status: localStorage.getItem("gradedGuitar.status.p_e2e"),
  }));
  const remaining = JSON.parse(after.profiles ?? "[]") as Array<{ id: string }>;
  expect(remaining.find((p) => p.id === "p_e2e")).toBeUndefined();
  expect(after.status).toBeNull();
});
