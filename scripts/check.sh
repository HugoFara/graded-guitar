#!/usr/bin/env bash
# Repository self-check. Runs locally and in CI.
# Validates that the foundation pieces required by spec Milestone 0 are present
# and that the syllabi JSON files conform to the schema.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
fail=0

require_file() {
  if [[ -f "$1" ]]; then
    green "  ok   $1"
  else
    red   "  MISS $1"
    fail=1
  fi
}

echo "==> Required top-level files"
require_file LICENSE
require_file README.md
require_file CONTRIBUTING.md
require_file CODE_OF_CONDUCT.md
require_file project-spec.md
require_file .gitignore

echo "==> Decision log"
require_file decisions/README.md
require_file decisions/template.md
require_file decisions/0001-license-mit.md
require_file decisions/0002-syllabi-sources.md
require_file decisions/0003-stack-deferred.md
require_file decisions/0004-deferrals.md
require_file decisions/0005-ingest-pipeline.md
require_file decisions/0006-github-as-source.md
require_file decisions/0007-mutopia-source.md
require_file decisions/0008-guitarloot-source.md
require_file decisions/0009-m2-grading-inputs.md
require_file decisions/0010-m2-close-with-dummy-labels.md
require_file decisions/0011-m3-stack.md

echo "==> Syllabi"
require_file syllabi/README.md
require_file syllabi/schema.json
require_file syllabi/rcm.json
require_file syllabi/trinity.json
require_file syllabi/abrsm.json

echo "==> Advisor agreement template"
require_file docs/ADVISOR.md
require_file docs/M2_ADVISOR_PACKET.md

echo "==> M1 ingest pipeline scripts"
require_file requirements.txt
require_file scripts/m1_common.py
require_file scripts/m1_discover_imslp.py
require_file scripts/m1_discover_github.py
require_file scripts/m1_discover_mutopia.py
require_file scripts/m1_discover_guitarloot.py
require_file scripts/m1_lilypond.py
require_file scripts/m1_fetch.py
require_file scripts/m1_validate.py
require_file scripts/m1_pre_check.py
require_file scripts/m2_features.py
require_file scripts/m2_feature_audit.py
require_file scripts/m2_label_bias.py
require_file scripts/m2_baseline_grader.py
require_file scripts/m2_dummy_advisor.py
require_file scripts/m2_train.py
require_file scripts/m2_eval.py
require_file scripts/m2_apply_to_manifest.py
require_file scripts/tests/test_m1_validation.py
require_file scripts/tests/test_m2.py
require_file corpus/README.md

echo "==> M3 web scaffold"
require_file web/package.json
require_file web/vite.config.ts
require_file web/tsconfig.json
require_file web/index.html
require_file web/src/main.ts
require_file web/src/App.svelte
require_file web/src/lib/manifest.ts
require_file web/src/lib/player.ts
require_file web/src/components/GradeBadge.svelte
require_file web/src/routes/CorpusList.svelte
require_file web/src/routes/PieceDetail.svelte
require_file web/scripts/copy-corpus.mjs
require_file web/scripts/render-report.mjs
require_file web/playwright.config.ts
require_file web/tests/e2e/render-smoke.spec.ts
require_file web/tests/e2e/tti.spec.ts
require_file corpus/m3_render_check.md
require_file .github/workflows/web.yml

echo "==> Syllabi JSON schema validation"
if command -v python3 >/dev/null 2>&1; then
  python3 scripts/validate_syllabi.py
else
  red "  python3 not found; cannot validate syllabi JSON"
  fail=1
fi

echo "==> M1 validation regression tests"
if command -v python3 >/dev/null 2>&1; then
  python3 scripts/tests/test_m1_validation.py || fail=1
else
  red "  python3 not found; cannot run M1 regression tests"
  fail=1
fi

echo "==> M2 regression tests"
if command -v python3 >/dev/null 2>&1; then
  python3 scripts/tests/test_m2.py || fail=1
else
  red "  python3 not found; cannot run M2 regression tests"
  fail=1
fi

if [[ "$fail" -ne 0 ]]; then
  red "FAILED"
  exit 1
fi
green "OK"
