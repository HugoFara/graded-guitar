import { test, expect } from "@playwright/test";
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

// Spec §7 M3: "Page loads to interactive in under 3 seconds on a standard
// broadband connection." We approximate "standard broadband" as a 10 Mbps /
// 40 ms round-trip throttle and measure the time from navigation start to
// when the corpus list is rendered (data-corpus-loaded set on the <ul>).
const TTI_BUDGET_MS = 3_000;

test("corpus list reaches interactive under TTI budget", async ({ browser }) => {
  const context = await browser.newContext();
  const client = await context.newCDPSession(await context.newPage());
  await client.send("Network.enable");
  await client.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: 40,
    downloadThroughput: (10 * 1024 * 1024) / 8,
    uploadThroughput: (2 * 1024 * 1024) / 8,
  });

  const page = (await context.pages())[0];

  const start = Date.now();
  // /browse is the corpus-list route; / now redirects to /onboard or
  // /feed depending on whether a level is stored (M4 step 4).
  await page.goto("/#/browse");
  const list = page.locator("[data-corpus-loaded]");
  await list.waitFor({ state: "attached", timeout: 10_000 });
  const ttiMs = Date.now() - start;

  const count = await list.getAttribute("data-corpus-count");
  const numericCount = Number(count);

  const outDir = resolve(here, "../../test-results");
  mkdirSync(outDir, { recursive: true });
  writeFileSync(
    resolve(outDir, "tti.json"),
    JSON.stringify(
      {
        ttiMs,
        budgetMs: TTI_BUDGET_MS,
        pieces: numericCount,
        throttle: { downloadMbps: 10, latencyMs: 40 },
        passed: ttiMs < TTI_BUDGET_MS,
      },
      null,
      2,
    ),
  );

  expect(numericCount).toBeGreaterThan(0);
  expect.soft(ttiMs, `TTI ${ttiMs} ms exceeds ${TTI_BUDGET_MS} ms budget`).toBeLessThan(
    TTI_BUDGET_MS,
  );
});
