#!/usr/bin/env bash
# Gate 1 (REAL): agentskills.io conformance lint for every skills/**/SKILL.md.
# Full contract: docs/harness-contract.md gate 1. Runs scripts/spec_lint.py
# per file (name/description/body/refs conformance + compliance flags:
# license, compliance, standards vs standards-map.yaml, gated, metadata).
# Exit 0 = all conformant.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
skills_dir="$repo_root/skills"

if [ ! -d "$skills_dir" ]; then
  echo "PASS gate1-spec-lint: no skills/ dir; nothing to lint"
  exit 0
fi

fail=0
checked=0
while IFS= read -r -d '' f; do
  checked=$((checked + 1))
  if ! python3 "$repo_root/scripts/spec_lint.py" "$f"; then
    fail=1
  fi
done < <(find "$skills_dir" -name SKILL.md -print0 2>/dev/null | sort -z)

if [ "$fail" -ne 0 ]; then
  echo "FAIL gate1-spec-lint: one or more SKILL.md failed" >&2
  exit 1
fi
echo "PASS gate1-spec-lint: ${checked} SKILL.md conformant (name/desc/body/refs/compliance-flags)"
