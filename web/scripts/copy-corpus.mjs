#!/usr/bin/env node
// Copies corpus/manifest.json + corpus/normalized/ into web/public/ as
// build-time static assets. Idempotent — only writes when source is newer
// or destination is missing. Run via package.json `predev` and `prebuild`.

import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, "..");
const repoRoot = path.resolve(webRoot, "..");

const manifestSrc = path.join(repoRoot, "corpus", "manifest.json");
const manifestDst = path.join(webRoot, "public", "manifest.json");
const normalizedSrc = path.join(repoRoot, "corpus", "normalized");
const normalizedDst = path.join(webRoot, "public", "musicxml");

async function statOr(p) {
  try {
    return await fs.stat(p);
  } catch {
    return null;
  }
}

async function copyIfNewer(src, dst) {
  const [s, d] = await Promise.all([statOr(src), statOr(dst)]);
  if (!s) throw new Error(`missing source: ${src}`);
  if (d && d.mtimeMs >= s.mtimeMs) return false;
  await fs.mkdir(path.dirname(dst), { recursive: true });
  await fs.copyFile(src, dst);
  return true;
}

// Files with `#` in their name break URL routing (Vite preview's SPA
// fallback decodes %23 and treats it as a fragment). Rewrite `#` → `--`
// at copy time and apply the same replacement in src/lib/manifest.ts
// when building piece URLs.
function safeName(name) {
  return name.replaceAll("#", "--");
}

async function syncDir(src, dst) {
  const s = await statOr(src);
  if (!s) {
    console.warn(`! ${src} missing — skipping (run M1 pipeline first)`);
    return { copied: 0, skipped: 0 };
  }
  await fs.mkdir(dst, { recursive: true });
  const entries = await fs.readdir(src, { withFileTypes: true });
  let copied = 0;
  let skipped = 0;
  for (const e of entries) {
    if (!e.isFile()) continue;
    const a = path.join(src, e.name);
    const b = path.join(dst, safeName(e.name));
    if (await copyIfNewer(a, b)) copied++;
    else skipped++;
  }
  return { copied, skipped };
}

async function main() {
  const manifestCopied = await copyIfNewer(manifestSrc, manifestDst);
  console.log(`manifest.json: ${manifestCopied ? "copied" : "up-to-date"}`);
  const r = await syncDir(normalizedSrc, normalizedDst);
  console.log(`normalized/: ${r.copied} copied, ${r.skipped} unchanged`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
