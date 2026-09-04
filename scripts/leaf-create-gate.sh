#!/usr/bin/env bash
# leaf-create-gate.sh — PER-LEAF CREATION GATE (founder mandate 2026-09-04).
#
# Every builder MUST run this on a leaf BEFORE committing it (wave brief
# s8 "Per-leaf completeness standard" enforcement + MAINTENANCE_AND_HANDOVER
# section 5a). Catches the defect classes found by the 2026-09-04 tree-wide
# audit so they can never recur:
#   1. missing SKILL.md sections (Pitfalls + Behavior contract gate 3)
#   2. misnamed logic file (test_ prefix on a logic module, no logic sibling)
#   3. "classified" / content-policy red-flag words in prose
#   4. missing logic/script/test pairing
#   5. pycache / editor junk tracked in git with the leaf
#   6. description missing action+use-when+trigger (gate-2 clause)
#   7. leaf not covered by corpus (fragment OR consolidated hit1-corpus.yaml)
#   8. missing eval/skill-eval/<leaf>.json record
#
# Usage:
#   bash scripts/leaf-create-gate.sh skills/avionics/data-bus/arinc429-bus-loading
# Exit 0 = leaf is creation-clean. Exit 1 = problems (printed). Exit 2 = usage.
set -uo pipefail

LEAF="${1:-}"
if [ -z "$LEAF" ]; then
  echo "usage: leaf-create-gate.sh <leaf-path-relative-to-repo-root>" >&2
  exit 2
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SKILL_FILE="$LEAF/SKILL.md"
FAILED=0

fail() { echo "  ✗ $1"; FAILED=1; }
pass() { echo "  ✓ $1"; }

echo "🔍 leaf-create-gate: $LEAF"
[ -f "$SKILL_FILE" ] || { echo "  ✗ SKILL.md not found at $SKILL_FILE" >&2; exit 1; }

# 1. House structure: Pitfalls + Behavior contract (gate 3) present
echo "— structure"
if grep -qE '^#{2,3} Pitfalls' "$SKILL_FILE"; then pass "Pitfalls section present"; else fail "missing '## Pitfalls' section (house structure)"; fi
if grep -qE 'Behavior contract \(gate 3\)' "$SKILL_FILE"; then pass "Behavior contract (gate 3) present"; else fail "missing '## Behavior contract (gate 3)' section"; fi

# 2. Logic/test pairing + naming
echo "— scripts"
SCRIPTS_DIR="$LEAF/scripts"
if [ -d "$SCRIPTS_DIR" ]; then
  LOGIC=$(find "$SCRIPTS_DIR" -maxdepth 1 -name '*.py' ! -name 'test_*.py' ! -path '*__pycache__*' | head -1)
  TEST=$(find "$SCRIPTS_DIR" -maxdepth 1 -name 'test_*.py' ! -path '*__pycache__*' | head -1)
  # True misname (test-point-matrix-design defect 2026-09-04): a test_*_logic.py
  # file with NO plain <x>_logic.py sibling — i.e. the logic module itself was
  # named test_<leaf>_logic.py. test_<x>_logic.py WITH a real <x>_logic.py
  # sibling is a correctly named TEST, not a defect.
  BAD_LOGIC=""
  for f in $(find "$SCRIPTS_DIR" -maxdepth 1 -name 'test_*_logic.py' ! -path '*__pycache__*'); do
    base=$(basename "$f")
    logic_part="${base#test_}"   # e.g. delta_fai_logic.py
    if [ ! -f "$SCRIPTS_DIR/$logic_part" ]; then
      BAD_LOGIC="$BAD_LOGIC $base"
    fi
  done
  if [ -n "$LOGIC" ]; then pass "logic script: $(basename "$LOGIC")"; else fail "no logic script (non-test .py)"; fi
  if [ -n "$TEST" ]; then pass "contract test: $(basename "$TEST")"; else fail "no contract test (test_*.py)"; fi
  if [ -n "$BAD_LOGIC" ]; then fail "logic file misnamed with test_ prefix (no matching logic sibling):$BAD_LOGIC (rename to <leaf>_logic.py)"; fi
  # run the test
  if [ -n "$TEST" ]; then
    if python3 "$TEST" >/dev/null 2>&1; then pass "contract test passes"; else fail "contract test FAILS: python3 $TEST"; fi
  fi
  PYCACHE_TRACKED=$(git ls-files "$SCRIPTS_DIR" | grep -E '__pycache__|\.pyc$' | head -1)
  if [ -n "$PYCACHE_TRACKED" ]; then fail "pycache tracked in git: $PYCACHE_TRACKED (git rm --cached before commit)"; else pass "no pycache tracked"; fi
else
  fail "no scripts/ directory"
fi

# 3. Content-policy red flags in SKILL.md prose
echo "— content policy"
if grep -qiE 'is classified|are classified|CLASSIFIED|SECRET//NOFORN|NOFORN|CONTROLLED UNCLASSIFIED|\bCUI\b' "$SKILL_FILE"; then fail "content-policy red flag (classified/CUI marking terms)"; else pass "no content-policy red flags"; fi

# 4. Frontmatter description gate-2 clause
echo "— description"
if grep -qE '^description:.*(when|Use when|use-when|trigger)' "$SKILL_FILE"; then pass "description has when/trigger clause"; else fail "description lacks when/trigger (gate-2 style)"; fi

# 5. Corpus coverage present (fragment OR consolidated corpus reference)
echo "— corpus"
LEAF_NAME=$(basename "$LEAF")
FRAG=$(ls eval/hit1-*"$LEAF_NAME"*.yaml 2>/dev/null | head -1)
if [ -n "$FRAG" ]; then
  pass "corpus fragment: $(basename "$FRAG")"
elif grep -qE "$LEAF_NAME|$LEAF" eval/hit1-corpus.yaml 2>/dev/null; then
  pass "corpus task in consolidated hit1-corpus.yaml"
else
  fail "no corpus coverage (add hit1-*<leaf>.yaml fragment OR consolidated task; 2 tasks with distinctive tokens)"
fi

# 6. Eval record present
echo "— eval"
if ls eval/skill-eval/"$LEAF_NAME".json >/dev/null 2>&1; then pass "eval record present"; else fail "no eval/skill-eval/<leaf>.json value-delta record"; fi

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "🟢 leaf-create-gate PASS — safe to commit: $LEAF"
  exit 0
else
  echo "🔴 leaf-create-gate FAIL — fix the above before committing: $LEAF"
  exit 1
fi
