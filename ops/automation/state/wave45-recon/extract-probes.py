#!/usr/bin/env python3
"""Wave-45 receipt fallback extractor (both probe batches): print the last
agent-final message block from each delegation live log."""
import glob
import os
import sys

for deleg in ("deleg_5e0653e2", "deleg_b57a8f5d"):
    # Resolve via env so no machine-local path is committed.
    # Run with HERMES_DELEGATION_LIVE=/path/to/delegation/live.
    base = os.environ.get("HERMES_DELEGATION_LIVE") or ""
    if not base:
        print("HERMES_DELEGATION_LIVE unset — skipping probe", file=sys.stderr)
        sys.exit(2)
    logdir = os.path.join(base, deleg)
    logs = sorted(glob.glob(os.path.join(logdir, "task-*.log")))
    for lp in logs:
        with open(lp, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        print("=" * 28, os.path.basename(lp), "=" * 28)
        tail = lines[-100:]
        for ln in tail:
            print(ln.rstrip()[:500])
        print()
