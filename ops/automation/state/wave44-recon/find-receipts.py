#!/usr/bin/env python3
"""Find all lines containing 'PROBE RECEIPTS' or the start of a candidate
report in probe logs, print them with generous width, in full."""
import glob, os

logdir = os.path.expanduser('~/.hermes/profiles/opsmanager/cache/delegation/live/deleg_2ff07eac')
logs = sorted(glob.glob(os.path.join(logdir, 'task-*.log')))
for lp in logs:
    with open(lp, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    hits = [i for i, ln in enumerate(lines) if 'PROBE RECEIPTS' in ln or 'NO_CANDIDATES' in ln or 'RECEIPTS (wave-44' in ln]
    print('=====', os.path.basename(lp), 'hits at lines:', hits)
    for i in hits:
        # print up to 200 lines after the hit or until next tool marker
        for j in range(i, min(i + 120, len(lines))):
            ln = lines[j]
            if j > i and (' tool     | -> ' in ln or ' result   | ' in ln):
                break
            print(ln.rstrip())
        print('--- end block ---')
