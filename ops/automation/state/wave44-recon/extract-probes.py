#!/usr/bin/env python3
"""Extract probe final summaries from delegation live logs: print the LAST
occurrence of an agent final message block (looks for 'PROBE RECEIPTS' or
'status=completed duration' summary content near the end)."""
import glob, os, re

logs = sorted(glob.glob(os.path.expanduser('~/.hermes/profiles/opsmanager/cache/delegation/live/deleg_2ff07eac/task-*.log')))
for lp in logs:
    with open(lp, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    print('=' * 28, os.path.basename(lp), '=' * 28)
    # print the last 60 lines but trim tool-result noise
    tail = lines[-80:]
    text = ''.join(tail)
    # cut each line to 400 chars
    for ln in tail:
        print(ln.rstrip()[:400])
    print()
