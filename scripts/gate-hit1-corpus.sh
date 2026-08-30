#!/usr/bin/env bash
# Gate 5 (STUB): Hit@1 corpus presence check.
# Full contract: docs/harness-contract.md. Real retrieval eval lands 2026-09-04.
# Today: verify eval/hit1-corpus.yaml exists and contains the 3 seed tasks.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
corpus="$repo_root/eval/hit1-corpus.yaml"

if [ ! -f "$corpus" ]; then
  echo "FAIL gate5-hit1 (STUB): $corpus missing" >&2
  exit 1
fi

python3 - "$corpus" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
tasks = d.get("tasks", [])
need = ["12U CubeSat", "weight-and-balance", "engine-overhaul"]
found = [t for t in tasks if any(n in t.get("query", "") for n in need)]
if len(found) != 3:
    sys.exit(f"FAIL gate5-hit1 (STUB): corpus has {len(found)}/3 seed tasks")
print("PASS gate5-hit1 (STUB): 3/3 seed tasks in corpus; real Hit@1 eval 09-04")
PY
