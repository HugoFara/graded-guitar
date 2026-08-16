import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// M8 practice mode (ADR 0018). The alignment core is unit-tested against
// synthetic ground truth in src/lib/listen/*.test.ts; what only a real
// browser can check is the integration — microphone permission, the
// AnalyserNode path, and that a take completes and analyzes without
// throwing.
//
// Chromium's fake device plays a steady test tone rather than guitar, so
// these tests assert that the pipeline runs end to end and produces a
// well-formed analysis. They deliberately do not assert alignment
// accuracy: a sine sweep has no relationship to the score, and a test
// that pretended otherwise would be measuring nothing.

const here = dirname(fileURLToPath(import.meta.url));
const manifestPath = resolve(here, "../../public/manifest.json");

type Piece = { candidate_id: string; metadata: { title: string } };
const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as {
  pieces: Piece[];
};

// A short, well-formed piece keeps the Viterbi pass quick.
const piece = manifest.pieces[0];
const practiceUrl = `/#/practice/${encodeURIComponent(piece.candidate_id)}`;

test.use({
  permissions: ["microphone"],
  launchOptions: {
    args: [
      "--use-fake-ui-for-media-stream",
      "--use-fake-device-for-media-stream",
    ],
  },
});

async function gotoPractice(page: Page) {
  await page.goto(practiceUrl);
  await expect(page.locator(".alphatab")).toBeVisible();
  // The score has to finish loading before the reference exists.
  await expect(page.getByRole("button", { name: /start listening/i })).toBeVisible({
    timeout: 30_000,
  });
}

test("practice page renders the score and offers the microphone", async ({ page }) => {
  await gotoPractice(page);
  await expect(page.getByRole("heading", { name: /^Practice:/ })).toBeVisible();
  await expect(page.getByText(/audio never leaves this browser/i)).toBeVisible();
});

test("the piece page links to practice mode", async ({ page }) => {
  await page.goto(`/#/piece/${encodeURIComponent(piece.candidate_id)}`);
  const link = page.getByRole("link", { name: /practice with mic/i });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page.getByRole("heading", { name: /^Practice:/ })).toBeVisible();
});

test("a take records, analyzes, and reports a result", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  await gotoPractice(page);
  await page.getByRole("button", { name: /start listening/i }).click();

  // Capture is live once the transport switches to the recording state.
  await expect(page.getByText(/● Recording/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/^Bar /)).toBeVisible();

  await page.waitForTimeout(3000);
  await page.getByRole("button", { name: /stop and analyze/i }).click();

  await expect(page.getByText(/of the piece reached/i)).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText(/of written tempo/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /record another take/i })).toBeVisible();

  expect(errors).toEqual([]);
});

test("an abandoned take is recorded as a lower bound, not an estimate", async ({
  page,
}) => {
  await gotoPractice(page);
  await page.getByRole("button", { name: /start listening/i }).click();
  await expect(page.getByText(/● Recording/)).toBeVisible({ timeout: 15_000 });

  // A three-second take of a test tone cannot reach the end of a real
  // piece, so the censoring notice is the expected outcome. This is the
  // check that the spec §7 M8 bound rule is wired to the UI at all.
  await page.waitForTimeout(3000);
  await page.getByRole("button", { name: /stop and analyze/i }).click();

  await expect(page.getByText(/of the piece reached/i)).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText(/at least.*this hard/i)).toBeVisible();
});

test("the take is persisted to the active profile", async ({ page }) => {
  await gotoPractice(page);
  await page.getByRole("button", { name: /start listening/i }).click();
  await expect(page.getByText(/● Recording/)).toBeVisible({ timeout: 15_000 });
  await page.waitForTimeout(2500);
  await page.getByRole("button", { name: /stop and analyze/i }).click();
  await expect(page.getByText(/of the piece reached/i)).toBeVisible({
    timeout: 60_000,
  });

  const stored = await page.evaluate(() => {
    const key = Object.keys(localStorage).find((k) =>
      k.startsWith("gradedGuitar.takes."),
    );
    return key ? JSON.parse(localStorage.getItem(key)!) : null;
  });

  expect(stored).not.toBeNull();
  const takes = stored[piece.candidate_id];
  expect(Array.isArray(takes)).toBe(true);
  expect(takes.length).toBeGreaterThan(0);
  expect(typeof takes[0].completed).toBe("boolean");
  expect(typeof takes[0].bar_count).toBe("number");
});

test("the privacy note documents the microphone", async ({ page }) => {
  await page.goto("/#/privacy");
  await expect(page.getByRole("heading", { name: /the microphone/i })).toBeVisible();
  await expect(page.getByText(/off unless you turn it on/i)).toBeVisible();
  await expect(page.getByText(/no audio recordings/i)).toBeVisible();
});
