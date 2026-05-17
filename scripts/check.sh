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

echo "==> Syllabi"
require_file syllabi/README.md
require_file syllabi/schema.json
require_file syllabi/rcm.json
require_file syllabi/trinity.json
require_file syllabi/abrsm.json

echo "==> Advisor agreement template"
require_file docs/ADVISOR.md

echo "==> Syllabi JSON schema validation"
if command -v python3 >/dev/null 2>&1; then
  python3 scripts/validate_syllabi.py
else
  red "  python3 not found; cannot validate syllabi JSON"
  fail=1
fi

if [[ "$fail" -ne 0 ]]; then
  red "FAILED"
  exit 1
fi
green "OK"
