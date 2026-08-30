#!/usr/bin/env bash
# Gate 3 (REAL): per-skill behavior contract tests (stdlib unittest, no network).
# Contract: docs/harness-contract.md gate 3. Discovers contract tests in
# scripts/test_*.py (repo-level) and any skill-shipped skills/**/scripts/test_*.py,
# enforces stdlib-only imports (scripts/check_stdlib_imports.py), runs each test
# with the stdlib unittest runner. Exit 0 = all tests pass.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"

roots=("$repo_root/scripts")
if [ -d "$repo_root/skills" ]; then
  roots+=("$repo_root/skills")
fi

fail=0
ran=0
while IFS= read -r -d '' t; do
  ran=$((ran + 1))
  echo "gate3: running $t"
  if ! python3 "$repo_root/scripts/check_stdlib_imports.py" "$t"; then
    fail=1
  fi
  if ! python3 "$t"; then
    fail=1
  fi
done < <(find "${roots[@]}" -name 'test_*.py' -print0 2>/dev/null | sort -z)

if [ "$ran" -eq 0 ]; then
  echo "FAIL gate3-pytest-contract: no contract tests found (skill 1 must ship scripts/test_do178c_levels.py)" >&2
  exit 1
fi
if [ "$fail" -ne 0 ]; then
  echo "FAIL gate3-pytest-contract: one or more test runs failed" >&2
  exit 1
fi
echo "PASS gate3-pytest-contract: ${ran} contract test(s) passed (stdlib unittest, offline)"
