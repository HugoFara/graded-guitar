import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

// Captures the screenshots embedded in the top-level README. Run with:
//   pnpm test:e2e screenshots
// then move the PNGs from test-results/screenshots/ into docs/screenshots/.

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "../../..");
const outDir = resolve(repoRoot, "docs/screenshots");

const manifest = JSON.parse(
  readFileSync(resolve(here, "../../public/manifest.json"), "utf-8"),
) as {
  pieces: Array<{
    candidate_id: string;
    metadata: { title: string; composer: string };
    grade?: string | null;
    model_grade?: string | null;
  }>;
};

function pickShowcasePiece() {
  // Prefer a curator-graded mid-level piece by a recognizable composer
  // so the screenshot reads as "real music", not a debug stub.
  const isMid = (g?: string | null) => g === "4" || g === "5" || g === "6";
  const composerRe = /sor|carcassi|aguado|carulli|t[aá]rrega|giuliani|pellegrini/i;
  const curated = manifest.pieces.find(
    (p) => isMid(p.grade) && composerRe.test(p.metadata.composer),
  );
  if (curated) return curated;
  const modelMid = manifest.pieces.find(
    (p) => isMid(p.model_grade) && composerRe.test(p.metadata.composer),
  );
  if (modelMid) return modelMid;
  return manifest.pieces.find((p) => isMid(p.model_grade)) ?? manifest.pieces[0];
}

test.use({ viewport: { width: 1280, height: 800 } });

test.beforeEach(async ({ context }) => {
  // Pre-seed a profile so the Landing redirect lands on /feed not /onboard,
  // and /feed actually has data. Mirrors lib/storage/profile.ts shape.
  await context.addInitScript(() => {
    const profile = {
      id: "demo",
      display_name: "Demo player",
      level: 5,
      created_at: new Date().toISOString(),
    };
    localStorage.setItem("gradedGuitar.profiles", JSON.stringify([profile]));
    localStorage.setItem("gradedGuitar.activeProfileId", "demo");
  });
});

test("onboard level picker", async ({ page }) => {
  await page.goto("/#/onboard");
  await page.waitForSelector("button.level");
  await page.screenshot({ path: `${outDir}/onboard.png`, fullPage: false });
});

test("feed at level 5", async ({ page }) => {
  await page.goto("/#/feed");
  await page.waitForSelector("li, article, .piece, .card", { timeout: 10_000 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${outDir}/feed.png`, fullPage: false });
});

test("browse full corpus", async ({ page }) => {
  await page.goto("/#/browse");
  await page.waitForSelector("li, article, table", { timeout: 10_000 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${outDir}/browse.png`, fullPage: false });
});

test("piece detail with notation", async ({ page }) => {
  test.setTimeout(90_000);
  const showcase = pickShowcasePiece();
  console.log(
    `screenshot showcase: ${showcase.metadata.composer} — ${showcase.metadata.title}`,
  );
  await page.goto(`/#/piece/${encodeURIComponent(showcase.candidate_id)}`);
  await page
    .waitForSelector('[data-render-state="rendered"]', { timeout: 60_000 })
    .catch(() => {});
  await page.waitForTimeout(2000);
  await page.screenshot({
    path: `${outDir}/piece-detail.png`,
    fullPage: false,
  });
});
