#!/usr/bin/env python3
"""List packs + leaves per chosen family (read-only helper for spec writing)."""
import os, sys

ROOT = os.path.expanduser("~/AeroSkills/skills")
fams = sys.argv[1:] if len(sys.argv) > 1 else sorted(os.listdir(ROOT))
for fam in fams:
    fp = os.path.join(ROOT, fam)
    if not os.path.isdir(fp):
        print(f"no family dir: {fam}")
        continue
    print(f"== {fam} ==")
    for pack in sorted(os.listdir(fp)):
        pp = os.path.join(fp, pack)
        if not os.path.isdir(pp):
            continue
        leaves = []
        for leaf in sorted(os.listdir(pp)):
            if os.path.isfile(os.path.join(pp, leaf, "SKILL.md")):
                leaves.append(leaf)
        print(f"  {pack} ({len(leaves)}): " + ", ".join(leaves))
