#!/usr/bin/env bash
# Gate 1 (STUB): agentskills.io conformance lint for SKILL.md files.
# Full contract: docs/harness-contract.md. Real conformance lands 2026-09-04.
# Today: for each SKILL.md found, verify frontmatter parses and carries
# name + description. Exit 0 when nothing exists to check or all pass.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
skills_dir="$repo_root/skills"

if [ ! -d "$skills_dir" ]; then
  echo "PASS gate1-spec-lint (STUB): no skills/ dir; nothing to lint"
  exit 0
fi

fail=0
checked=0
while IFS= read -r -d '' f; do
  checked=$((checked + 1))
  if ! python3 - "$f" <<'PY'
import sys, pathlib, yaml
p = pathlib.Path(sys.argv[1])
text = p.read_text()
if not text.startswith("---"):
    sys.exit(f"FAIL {p}: missing frontmatter delimiter")
parts = text.split("---", 2)
if len(parts) < 3:
    sys.exit(f"FAIL {p}: frontmatter not closed")
try:
    fm = yaml.safe_load(parts[1])
except Exception as e:
    sys.exit(f"FAIL {p}: frontmatter yaml error: {e}")
if not isinstance(fm, dict):
    sys.exit(f"FAIL {p}: frontmatter not a mapping")
for k in ("name", "description"):
    if not fm.get(k):
        sys.exit(f"FAIL {p}: frontmatter missing '{k}'")
print(f"PASS gate1-spec-lint (STUB): {p} name={fm['name']}")
PY
  then
    fail=1
  fi
done < <(find "$skills_dir" -name SKILL.md -print0 2>/dev/null)

if [ "$fail" -ne 0 ]; then
  echo "FAIL gate1-spec-lint: one or more SKILL.md failed" >&2
  exit 1
fi
if [ "$checked" -eq 0 ]; then
  echo "PASS gate1-spec-lint (STUB): no SKILL.md present; contract docs/harness-contract.md"
else
  echo "PASS gate1-spec-lint (STUB): ${checked} SKILL.md checked"
fi
