#!/usr/bin/env node
// Deploy the local build to the gh-pages branch.
//
// Why this exists: the M3 corpus (corpus/normalized/, ~110 MB) is
// gitignored, so a hosted CI runner builds the site without any
// MusicXML files (404 on every piece). Until we settle on a corpus
// strategy that works on CI (see ADR 0011 open items), deploys are
// done from a developer machine that has the corpus checked out.
//
// Safety: refuses to deploy if web/public/musicxml/ is empty —
// otherwise we'd publish the same broken site CI produces.
//
// We bypass `gh-pages` npm (which silently dropped the musicxml/
// directory under globby's filtering) and use direct git via a
// throwaway worktree. The orphan-init branch with a fresh tree
// keeps gh-pages history short.

import { promises as fs, existsSync } from "node:fs";
import path from "node:path";
import os from "node:os";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, "..");
const repoRoot = path.resolve(webRoot, "..");

const publicMusicxml = path.join(webRoot, "public", "musicxml");
const distDir = path.join(webRoot, "dist");

function sh(cmd, args, opts = {}) {
  execFileSync(cmd, args, { stdio: "inherit", cwd: webRoot, ...opts });
}

function shOut(cmd, args, opts = {}) {
  return execFileSync(cmd, args, { cwd: repoRoot, ...opts }).toString().trim();
}

async function main() {
  if (!existsSync(publicMusicxml)) {
    console.error(`✗ ${publicMusicxml} missing — run \`pnpm dev\` once to populate it, or rerun M1.`);
    process.exit(1);
  }
  const xmlCount = (await fs.readdir(publicMusicxml)).length;
  if (xmlCount === 0) {
    console.error("✗ web/public/musicxml/ is empty — refusing to deploy a music-less site.");
    process.exit(1);
  }
  console.log(`✓ ${xmlCount} MusicXML files staged`);

  console.log("→ pnpm run build");
  sh("pnpm", ["run", "build"]);

  const builtXml = (await fs.readdir(path.join(distDir, "musicxml"))).length;
  if (builtXml !== xmlCount) {
    console.error(`✗ dist/musicxml has ${builtXml} files but public/musicxml has ${xmlCount}`);
    process.exit(1);
  }

  const sha = shOut("git", ["rev-parse", "--short", "HEAD"]);
  const stamp = new Date().toISOString();
  await fs.writeFile(
    path.join(distDir, "deploy.json"),
    JSON.stringify({ sha, deployedAt: stamp, files: builtXml }, null, 2),
  );
  await fs.writeFile(path.join(distDir, ".nojekyll"), "");

  const remote = shOut("git", ["remote", "get-url", "origin"]);
  const work = await fs.mkdtemp(path.join(os.tmpdir(), "gg-ghpages-"));
  console.log(`→ syncing dist/ → gh-pages via ${work}`);

  // Start fresh each time: orphan branch with single commit; gh-pages
  // history stays short and storage stays bounded.
  sh("git", ["init", "-q", "-b", "gh-pages", work], { cwd: undefined });
  sh("git", ["-C", work, "remote", "add", "origin", remote], { cwd: undefined });

  // Copy dist/ into work/.
  await fs.cp(distDir, work, { recursive: true, errorOnExist: false });

  sh("git", ["-C", work, "add", "-A"], { cwd: undefined });
  sh("git", [
    "-C", work,
    "-c", "user.name=graded-guitar deploy",
    "-c", "user.email=github@hugofara.net",
    "commit", "-q", "-m", `Deploy ${sha} (${builtXml} pieces)`,
  ], { cwd: undefined });
  sh("git", ["-C", work, "push", "-f", "origin", "gh-pages"], { cwd: undefined });

  await fs.rm(work, { recursive: true, force: true });

  console.log("✓ deployed");
  console.log("  https://hugofara.github.io/graded-guitar/");
  console.log("  Pages picks up the new commit in ~30s.");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
