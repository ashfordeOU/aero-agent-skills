#!/usr/bin/env python3
"""Wave-43 router parity check: table rows per family == leaf dirs per family."""
import os, re, subprocess

ROOT = os.path.expanduser("~/AeroSkills/skills")
fams = ["flight-test-operations", "propulsion", "gnc-autonomy", "aerodynamics", "structures"]
ok = True
for fam in fams:
    # count leaves: SKILL.md at depth >= 2 under family (pack/leaf/SKILL.md), excluding the router itself
    leaves = 0
    for root, dirs, files in os.walk(os.path.join(ROOT, fam)):
        depth = root[len(os.path.join(ROOT, fam)):].count(os.sep)
        for fn in files:
            if fn == "SKILL.md" and depth >= 2:
                leaves += 1
    txt = open(os.path.join(ROOT, fam, "SKILL.md"), encoding="utf-8").read()
    rows = len(re.findall(r"(?m)^\| " + fam + r"/", txt))
    state = "OK" if rows == leaves else "MISMATCH"
    if state != "OK":
        ok = False
    print(f"{state} {fam}: rows={rows} leaves={leaves}")
print("PARITY:", "PASS" if ok else "FAIL")
