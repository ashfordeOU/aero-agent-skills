#!/usr/bin/env bash
# Gate 2 (REAL): description lint (what+when+trigger) per docs/harness-contract.md
# gate 2 and brief 03 section 4 (descriptions are the router). Runs
# scripts/desc_lint.py per SKILL.md. Exit 0 = all descriptions pass.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
skills_dir="$repo_root/skills"

if [ ! -d "$skills_dir" ]; then
  echo "PASS gate2-desc-lint: no skills/ dir; nothing to lint"
  exit 0
fi

fail=0
checked=0
while IFS= read -r -d '' f; do
  checked=$((checked + 1))
  if ! python3 "$repo_root/scripts/desc_lint.py" "$f"; then
    fail=1
  fi
done < <(find "$skills_dir" -name SKILL.md -print0 2>/dev/null | sort -z)

if [ "$fail" -ne 0 ]; then
  echo "FAIL gate2-desc-lint: one or more descriptions failed" >&2
  exit 1
fi
echo "PASS gate2-desc-lint: ${checked} description(s) pass (action/what + use-when + trigger, 50-150 words)"
