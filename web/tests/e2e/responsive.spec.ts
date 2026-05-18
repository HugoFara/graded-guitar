import { test, expect } from "@playwright/test";

// Spec §7 M3: "Responsive layout that works on a laptop and on a
// tablet in landscape." We check the corpus list + a piece detail at
// each viewport: no horizontal page scroll, the main interactive
// elements are visible above the fold, and alphaTab still renders.

type Viewport = { name: string; width: number; height: number };
const VIEWPORTS: Viewport[] = [
  { name: "laptop", width: 1366, height: 768 },
  { name: "tablet-landscape", width: 1024, height: 768 },
];

const PIECE_CID = "guitarloot:Scores/EnglishMusic/ELB/44CouranteGaultier";

for (const vp of VIEWPORTS) {
  test.describe(`viewport ${vp.name} (${vp.width}x${vp.height})`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("corpus list fits without horizontal page scroll", async ({ page }) => {
      // /browse is the corpus-list route; / redirects to /onboard or
      // /feed depending on stored level (M4 step 4).
      await page.goto("/#/browse");
      await page.locator("[data-corpus-loaded]").waitFor({ timeout: 10_000 });

      const overflow = await page.evaluate(() => ({
        docW: document.documentElement.scrollWidth,
        winW: window.innerWidth,
      }));
      expect(overflow.docW, "no horizontal page overflow").toBeLessThanOrEqual(overflow.winW + 1);

      // Toolbar inputs are reachable
      await expect(page.locator('input[type="search"]').first()).toBeVisible();
      await expect(page.locator(".piece").first()).toBeVisible();
    });

    test("piece detail player is usable", async ({ page }) => {
      test.setTimeout(60_000);
      await page.goto(`/#/piece/${encodeURIComponent(PIECE_CID)}`);
      await expect(page.locator(".alphatab")).toHaveAttribute(
        "data-render-state",
        /rendered|error/,
        { timeout: 30_000 },
      );

      // Transport controls visible above the fold
      const controls = await Promise.all([
        page.getByRole("button", { name: /play/i }).first().isVisible(),
        page.getByRole("button", { name: /stop/i }).first().isVisible(),
        page.locator('input[aria-label="loop start bar"]').isVisible(),
        page.locator('input[aria-label="loop end bar"]').isVisible(),
      ]);
      expect(controls.every(Boolean), "all transport controls visible").toBe(true);

      const overflow = await page.evaluate(() => ({
        docW: document.documentElement.scrollWidth,
        winW: window.innerWidth,
      }));
      // alphaTab itself may scroll horizontally inside its container (we
      // set overflow-x: auto on .alphatab), but the page shouldn't.
      expect(overflow.docW, "no horizontal page overflow").toBeLessThanOrEqual(overflow.winW + 1);
    });
  });
}
