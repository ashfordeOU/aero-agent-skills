#!/usr/bin/env python3
"""Pre-merge Hit@1 simulation: run router_eval on a TEMP corpus that appends
all on-disk wave41 fragments to the live corpus. Does NOT modify the real
corpus. Catches new-task misroutes AND pre-existing-task theft before merge.
Usage: python3 ops/automation/state/wave41-sim-merge.py [--keep]
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
CORPUS = ROOT / "eval" / "hit1-corpus.yaml"
FRAG_GLOB = "eval/hit1-wave41-*.yaml"

def main():
    text = CORPUS.read_text(encoding="utf-8")
    tasks_m = re.search(r"(?m)^tasks:\s*$", text)
    pins_m = re.search(r"(?m)^future_pins:\s*$", text)
    if not tasks_m or not pins_m:
        print("FAIL: corpus blocks not found", file=sys.stderr)
        return 1
    tasks_block = text[tasks_m.start() : pins_m.start()]
    pins_block = text[pins_m.start():]

    fragments = sorted(ROOT.glob(FRAG_GLOB))
    if not fragments:
        print("no fragments on disk (expected after merge or before build)")
        return 0

    entries = []
    for frag in fragments:
        ft = frag.read_text(encoding="utf-8")
        items = re.findall(r"(?ms)^  - id: (\S+)\n(.*?)(?=^  - id:|\Z)", ft)
        for tid, body in items:
            entries.append(f"  - id: {tid}\n{body.rstrip()}\n")

    new_block = tasks_block.rstrip() + "\n" + "".join(entries) + "\n"
    sim_text = text[: tasks_m.start()] + new_block + pins_block

    keep = "--keep" in sys.argv
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="wave41sim_"))
    sim_corpus = tmpdir / "hit1-corpus-sim.yaml"
    sim_corpus.write_text(sim_text, encoding="utf-8")

    cmd = ["python3", str(ROOT / "scripts/router_eval.py"), str(sim_corpus), str(ROOT / "skills")]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    out = proc.stdout + proc.stderr
    # Summarize: count PASS/FAIL, print FAIL lines
    fails = [l for l in out.splitlines() if "FAIL" in l or ("top1=" in l and "PASS" not in l)]
    if fails:
        print(f"SIM FAIL: {len(fails)} problem lines")
        for l in fails[:40]:
            print(" ", l[:300])
        rc = 2
    else:
        m = re.search(r"PASS gate5-hit1: (\d+)/(\d+) tasks Hit@1", out)
        print(f"SIM PASS: {m.group(0) if m else 'all tasks Hit@1'} ({len(fragments)} fragments, {len(entries)} new tasks)")
        rc = 0
    if keep:
        print("sim corpus at", sim_corpus)
    else:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return rc

if __name__ == "__main__":
    sys.exit(main())
