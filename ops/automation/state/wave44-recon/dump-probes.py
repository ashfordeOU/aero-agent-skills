#!/usr/bin/env python3
"""Dump each probe's FINAL summary (full text) to a per-task file under wave44-recon."""
import glob, os, re

logdir = os.path.expanduser('~/.hermes/profiles/<PROFILE>/cache/delegation/live/deleg_2ff07eac')
outdir = os.path.expanduser('~/AeroSkills/ops/automation/state/wave44-recon')
logs = sorted(glob.glob(os.path.join(logdir, 'task-*.log')))
for lp in logs:
    with open(lp, encoding='utf-8', errors='replace') as f:
        content = f.read()
    # find last occurrence of 'summary:' that belongs to a final/agent message
    markers = [m.start() for m in re.finditer(r'summary:\s*(##\s|.*PROBE RECEIPTS)', content)]
    # fall back to the last 'final    |' block
    idx = content.rfind('final    | status=completed')
    block = content[idx:] if idx != -1 else content[-4000:]
    m = re.search(r'(?:final\s+\|\s+)?status=completed duration=\S+ summary:\s*(.*)$', block, re.S)
    out = os.path.join(outdir, os.path.basename(lp).replace('.log', '-receipt.md'))
    with open(out, 'w', encoding='utf-8') as f:
        if m:
            f.write(m.group(1))
        else:
            # last 3000 chars as fallback
            f.write(content[-3000:])
    print(os.path.basename(out), os.path.getsize(out), 'bytes')
