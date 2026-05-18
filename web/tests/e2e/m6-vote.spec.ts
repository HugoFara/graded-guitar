import { test, expect } from "@playwright/test";

// Spec §7 M6 follow-up (ADR 0013): the grade-disagreement vote
// affordance is the path to a real grading signal. End-to-end:
//   - "Harder" persists across reload and shows in Library
//   - The vote record carries the grade snapshot (grade_at_record /
//     grade_source_at_record) at write time
//   - Clearing the vote (clicking the active button again) deletes
//     the record

async function seedProfile(page) {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.clear();
    const id = "p_e2e_vote";
    localStorage.setItem(
      "gradedGuitar.profiles",
      JSON.stringify([
        {
          id,
          display_name: "VoteE2E",
          created_at: "2026-01-01T00:00:00Z",
          level: 5,
        },
      ]),
    );
    localStorage.setItem("gradedGuitar.activeProfileId", id);
  });
}

test("grade-disagreement vote persists and appears in Library", async ({ page }) => {
  await seedProfile(page);
  await page.goto("/#/feed");
  await page.locator("[data-feed-loaded]").waitFor({ timeout: 10_000 });

  const firstCard = page.locator("a.card").first();
  const firstHref = await firstCard.getAttribute("href");
  await firstCard.click();
  await page.locator(".alphatab").waitFor({ timeout: 30_000 });

  await page.locator('[data-vote="harder"]').click();

  // Vote should round-trip into localStorage with a grade snapshot
  const stored = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("gradedGuitar.votes.p_e2e_vote") ?? "{}"),
  );
  const cids = Object.keys(stored);
  expect(cids).toHaveLength(1);
  const rec = stored[cids[0]];
  expect(rec.vote).toBe("harder");
  expect(typeof rec.updated_at).toBe("string");
  // The pieces in the e2e corpus all carry at least a model_grade, so
  // the snapshot must be present.
  expect(typeof rec.grade_at_record).toBe("string");
  expect(typeof rec.grade_source_at_record).toBe("string");

  // Reload — active state must survive
  await page.reload();
  await page.locator(".alphatab").waitFor({ timeout: 30_000 });
  await expect(page.locator('[data-vote="harder"]')).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  // Library "Grade votes" tab shows the row, linking back to the piece
  await page.goto("/#/library");
  await page.getByRole("tab", { name: /Grade votes/ }).click();
  await page.locator("[data-votes-loaded]").waitFor({ timeout: 10_000 });
  await expect(page.locator(`a.row[href="${firstHref}"]`)).toHaveCount(1);
  await expect(page.locator(".vote-chip.vote-harder")).toBeVisible();
});

test("clicking the active vote a second time clears it", async ({ page }) => {
  await seedProfile(page);
  await page.goto("/#/feed");
  await page.locator("[data-feed-loaded]").waitFor({ timeout: 10_000 });
  await page.locator("a.card").first().click();
  await page.locator(".alphatab").waitFor({ timeout: 30_000 });

  await page.locator('[data-vote="easier"]').click();
  await expect(page.locator('[data-vote="easier"]')).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.locator('[data-vote="easier"]').click();
  await expect(page.locator('[data-vote="easier"]')).toHaveAttribute(
    "aria-pressed",
    "false",
  );

  const stored = await page.evaluate(() =>
    localStorage.getItem("gradedGuitar.votes.p_e2e_vote"),
  );
  // Either the key is gone or the map is empty — both acceptable.
  expect(stored == null || stored === "{}").toBe(true);
});
