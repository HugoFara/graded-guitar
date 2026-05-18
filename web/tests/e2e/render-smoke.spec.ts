import { test, expect, type ConsoleMessage } from "@playwright/test";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const manifestPath = resolve(here, "../../public/manifest.json");

type Piece = {
  candidate_id: string;
  metadata: { title: string; composer: string };
  source: string;
  normalized_path: string;
};
type Manifest = { pieces: Piece[] };

// Mulberry32 — deterministic PRNG so the same 10 pieces are tested every run.
function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function sample<T>(arr: T[], n: number, seed: number): T[] {
  const r = rng(seed);
  const indices = new Set<number>();
  while (indices.size < Math.min(n, arr.length)) {
    indices.add(Math.floor(r() * arr.length));
  }
  return [...indices].map((i) => arr[i]);
}

const SEED = 1;
const N = 10;
const PER_PIECE_TIMEOUT = 50_000;

test.setTimeout(60_000);

const manifest = JSON.parse(readFileSync(manifestPath, "utf-8")) as Manifest;
const sampled = sample(manifest.pieces, N, SEED);

type Result = {
  cid: string;
  title: string;
  composer: string;
  source: string;
  status: "rendered" | "error" | "timeout";
  durationMs: number;
  consoleErrors: string[];
  pageError?: string;
  svgCount?: number;
  finalRenderState?: string | null;
  errorText?: string | null;
};

const perPieceDir = resolve(here, "../../test-results/render-pieces");
const aggregatePath = resolve(here, "../../test-results/render-smoke.json");

function appendResult(r: Result) {
  mkdirSync(perPieceDir, { recursive: true });
  const safe = r.cid.replace(/[^a-zA-Z0-9._-]/g, "_");
  writeFileSync(resolve(perPieceDir, `${safe}.json`), JSON.stringify(r, null, 2));
}

test.afterAll(async () => {
  const all: Result[] = [];
  if (existsSync(perPieceDir)) {
    const fs = await import("node:fs");
    for (const f of fs.readdirSync(perPieceDir)) {
      if (!f.endsWith(".json")) continue;
      all.push(JSON.parse(readFileSync(resolve(perPieceDir, f), "utf-8")));
    }
  }
  writeFileSync(
    aggregatePath,
    JSON.stringify(
      {
        seed: SEED,
        n: N,
        manifestPieces: manifest.pieces.length,
        results: all,
      },
      null,
      2,
    ),
  );
});

for (const piece of sampled) {
  test(`renders: ${piece.metadata.composer} — ${piece.metadata.title}`, async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg: ConsoleMessage) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    let pageError: string | undefined;
    page.on("pageerror", (err) => {
      pageError = err.message;
    });

    const cid = encodeURIComponent(piece.candidate_id);
    const start = Date.now();
    await page.goto(`/#/piece/${cid}`);

    const container = page.locator(".alphatab");
    let status: Result["status"];
    try {
      await container.waitFor({ state: "attached", timeout: 10_000 });
      await expect(container).toHaveAttribute("data-render-state", /rendered|error/, {
        timeout: PER_PIECE_TIMEOUT,
      });
      const finalState = await container.getAttribute("data-render-state");
      status = finalState === "rendered" ? "rendered" : "error";
    } catch {
      status = "timeout";
    }

    const durationMs = Date.now() - start;

    // Snapshot DOM state for debugging slow/failed pieces. After a
    // timeout Playwright may already have closed the page, so wrap each
    // probe — we still want the result row even if some probes fail.
    const svgCount = await page.locator(".alphatab svg").count().catch(() => 0);
    const renderStateAttr = await container.getAttribute("data-render-state").catch(() => null);
    const errorTextLoc = page.locator(".error");
    const errorText = await (async () => {
      try {
        return (await errorTextLoc.count()) > 0
          ? await errorTextLoc.first().textContent()
          : null;
      } catch {
        return null;
      }
    })();

    appendResult({
      cid: piece.candidate_id,
      title: piece.metadata.title,
      composer: piece.metadata.composer,
      source: piece.source,
      status,
      durationMs,
      consoleErrors,
      pageError,
      svgCount,
      finalRenderState: renderStateAttr,
      errorText,
    });

    expect.soft(status, `${piece.candidate_id} failed to render`).toBe("rendered");
    expect.soft(pageError ?? "", `${piece.candidate_id} threw`).toBe("");
  });
}
