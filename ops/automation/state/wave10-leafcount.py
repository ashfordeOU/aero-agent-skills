#!/usr/bin/env python3
"""Wave-10: count leaf SKILL.md files per family and list leaf paths."""
import os

ROOT = "/Users/enterprisehq/AeroSkills/skills"
families = [
    "aerodynamics",
    "flight-test-operations",
    "propulsion",
    "flight-mechanics",
    "space-systems",
    "systems-engineering-safety",
    "cross-cutting",
    "gnc-autonomy",
    "manufacturing-quality",
    "vehicle-design",
    "structures",
    "avionics",
]

for fam in families:
    famdir = os.path.join(ROOT, fam)
    if not os.path.isdir(famdir):
        print(f"{fam}: MISSING")
        continue
    leaves = []
    for dirpath, dirnames, filenames in os.walk(famdir):
        if "SKILL.md" in filenames:
            rel = os.path.relpath(dirpath, famdir)
            if rel != ".":
                leaves.append(rel)
    leaves.sort()
    print(f"{fam}: {len(leaves)} leaves")
    for leaf in leaves:
        print(f"  {leaf}")
