#!/usr/bin/env bash
# Gate 5 (REAL): Hit@1 corpus eval (deterministic, offline).
# Contract: docs/harness-contract.md gate 5. Reads eval/hit1-corpus.yaml,
# resolves each task via the flat+tags router (scripts/router_eval.py) against
# asserts top-1 == expected_skill for EVERY case in eval/: the corpus and
# every per-leaf hit1-<slug>.yaml fragment. The fragments used to be graded
# by nothing, which left most leaves asserted by no executed case at all.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
corpus="$repo_root/eval"
skills_dir="$repo_root/skills"

if [ ! -d "$corpus" ]; then
  echo "FAIL gate5-hit1: $corpus missing" >&2
  exit 1
fi
if [ ! -d "$skills_dir" ]; then
  echo "FAIL gate5-hit1: $skills_dir missing; cannot resolve" >&2
  exit 1
fi
exec python3 "$repo_root/scripts/router_eval.py" "$corpus" "$skills_dir"
