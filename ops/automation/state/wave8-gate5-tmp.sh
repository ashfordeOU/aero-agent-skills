#!/usr/bin/env bash
# Wave-8 isolated gate-5 (Hit@1) runner for parallel leaf subagents.
# Usage: bash ops/automation/state/wave8-gate5-tmp.sh <leaf-rel-path> <fragment-rel-path>
#   e.g. bash ops/automation/state/wave8-gate5-tmp.sh \
#          structures/fatigue/goodman-diagram eval/hit1-wave8-goodman-diagram.yaml
#
# Why: parallel leaf agents share the working tree, so gating on the live
# tree sees other agents' half-written leaves (false failures) and misses
# the agent's own untracked leaf. This script builds an isolated scratch
# tree from the committed index (git checkout-index), copies THIS leaf and
# its scripts in, appends THIS fragment's 2 eval tasks to a scratch copy of
# the corpus, then runs router_eval.py (gate 5). Deterministic, offline.
# Exit 0 = every corpus task (committed + own 2) Hit@1.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
leaf="$1"
frag="$2"
scratch="/tmp/w8-g5-$(echo "$leaf" | tr '/' '-')"

rm -rf "$scratch"
mkdir -p "$scratch"
cd "$repo_root"

git checkout-index -a -f --prefix="$scratch/"

# Copy this agent's own untracked leaf + scripts into the scratch tree.
mkdir -p "$scratch/skills/$(dirname "$leaf")"
cp -R "skills/$leaf" "$scratch/skills/$leaf"

# Scratch corpus = committed corpus + this fragment's tasks (2).
python3 - "$scratch" "$frag" <<'PY'
import pathlib
import re
import sys

scratch = pathlib.Path(sys.argv[1])
frag = pathlib.Path(sys.argv[2])
corpus = scratch / "eval" / "hit1-corpus.yaml"
text = corpus.read_text(encoding="utf-8")
ft = frag.read_text(encoding="utf-8")
items = re.findall(r"(?ms)^  - id: (\S+)\n(.*?)(?=^  - id:|\Z)", ft)
if len(items) != 2:
    print("FAIL: fragment %s has %d tasks, expected 2" % (frag.name, len(items)), file=sys.stderr)
    sys.exit(1)
pins = re.search(r"(?m)^future_pins:\s*$", text)
if not pins:
    print("FAIL: no future_pins: block in corpus", file=sys.stderr)
    sys.exit(1)
block = text[: pins.start()].rstrip() + "\n"
for tid, body in items:
    block += "  - id: %s\n%s\n" % (tid, body.rstrip())
block += "\n" + text[pins.start():]
corpus.write_text(block, encoding="utf-8")
PY

python3 "$scratch/scripts/router_eval.py" "$scratch/eval/hit1-corpus.yaml" "$scratch/skills"
