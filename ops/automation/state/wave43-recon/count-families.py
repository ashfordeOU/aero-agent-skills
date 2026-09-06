#!/usr/bin/env python3
"""Wave-43 recon: baseline tree counts at HEAD 916485c0 (read-only)."""
import os, subprocess, sys

ROOT = os.path.expanduser("~/AeroSkills")
os.chdir(ROOT)

def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip()

# sanity: HEAD
head = sh("git rev-parse --short HEAD")
print(f"HEAD={head}")

# family dirs and their immediate children (packs)
fam_dir = os.path.join(ROOT, "skills")
families = sorted(os.listdir(fam_dir))
total_sk = 0
for fam in families:
    fp = os.path.join(fam_dir, fam)
    if not os.path.isdir(fp):
        continue
    # count SKILL.md at any depth >= 2 under family
    n = 0
    packs = []
    for d in sorted(os.listdir(fp)):
        dp = os.path.join(fp, d)
        if os.path.isdir(dp):
            packs.append(d)
            for root, dirs, files in os.walk(dp):
                for fn in files:
                    if fn == "SKILL.md":
                        n += 1
    print(f"family={fam} leafish_sk_md={n} packs={len(packs)}")

print("---- top-level files in skills/ (routers?) ----")
for fn in sorted(os.listdir(fam_dir)):
    fp = os.path.join(fam_dir, fn)
    if os.path.isfile(fp):
        print(fn)
