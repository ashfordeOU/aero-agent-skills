#!/usr/bin/env python3
"""Wave-43 close precondition: verify the 16 new leaves each have their six
artifacts on the HEAD chain and exactly one ledger row; report totals."""
import os, re, subprocess, sys

ROOT = os.path.expanduser("~/AeroSkills")
os.chdir(ROOT)

leaves = [
    "flight-test-operations/envelope/vmu-determination",
    "flight-test-operations/performance/rotorcraft-forward-flight-climb-test",
    "flight-test-operations/performance/rotorcraft-height-velocity-diagram-test",
    "propulsion/rocket/rocket-nozzle-divergence-loss",
    "propulsion/turbofan/turbofan-design-point",
    "gnc-autonomy/navigation/gnss-doppler-velocity-positioning",
    "gnc-autonomy/estimation-filtering/process-noise-discretization",
    "gnc-autonomy/estimation-filtering/imu-static-calibration",
    "gnc-autonomy/navigation/tightly-coupled-ins-gnss",
    "aerodynamics/high-speed/fanno-flow",
    "aerodynamics/high-speed/rayleigh-flow",
    "aerodynamics/boundary-layer/unsteady-laminar-stokes-layers",
    "structures/fem/crippling-analysis",
    "structures/fem/hertzian-contact-stress",
    "structures/fem/metallic-fastener-joints",
    "structures/fem/plastic-collapse-analysis",
]

def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip()

tracked = set(sh("git ls-files").splitlines())
ledger = open("eval/skill-ratings.md", encoding="utf-8").read()

ok = True
for leaf in leaves:
    fam = leaf.split("/")[0]
    name = leaf.split("/")[-1]
    short = name.replace("-", "_")
    artifacts = [
        f"skills/{leaf}/SKILL.md",
        f"skills/{leaf}/scripts/{short}_logic.py",
        f"skills/{leaf}/scripts/test_{short}.py",
        f"eval/hit1-wave43-{name}.yaml",
        f"eval/skill-eval/{name}.json",
    ]
    missing = [a for a in artifacts if a not in tracked]
    rowcount = len(re.findall(r"^\| \d+ \| " + re.escape(leaf) + r" \|", ledger, re.M))
    status = "OK" if not missing and rowcount == 1 else "BAD"
    if status == "BAD":
        ok = False
    print(f"{status} {leaf} rows={rowcount} missing={missing}")

# totals
sk_md = len([f for f in tracked if f.startswith("skills/") and f.endswith("/SKILL.md")])
rows = len(re.findall(r"(?m)^\| \d+ \|", ledger))
header = re.search(r"Total skills rated:\s*(\d+)", ledger)
print(f"SKILL.md tracked: {sk_md} (expect 609 = 593 + 16)")
print(f"ledger rows: {rows} (expect 597); header says {header.group(1) if header else '?'}")
print("OVERALL:", "PASS" if ok and sk_md == 609 and rows == 597 else "CHECK NEEDED")
