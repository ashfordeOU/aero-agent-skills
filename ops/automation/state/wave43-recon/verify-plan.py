#!/usr/bin/env python3
"""Wave-43 leaf-plan verification: candidate paths must NOT exist; standards ids MUST exist."""
import os, re, sys

ROOT = os.path.expanduser("~/AeroSkills")

candidates = [
    "flight-test-operations/envelope/vmu-determination",
    "flight-test-operations/performance/rotorcraft-forward-flight-climb-test",
    "flight-test-operations/performance/rotorcraft-height-velocity-diagram-test",
    "propulsion/rocket/rocket-nozzle-divergence-loss",
    "propulsion/turbofan/turbofan-design-point",
    "propulsion/turbofan/mixed-flow-exhaust",
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
reserve = [
    "flight-test-operations/performance/balked-landing-flight-test",
    "flight-test-operations/performance/rotorcraft-category-a-oei-flight-test",
    "gnc-autonomy/optimal-control/ilqr-ddp",
    "gnc-autonomy/navigation/terrain-referenced-navigation",
    "aerodynamics/boundary-layer/laminar-far-wake-free-shear",
    "structures/fem/statically-indeterminate-analysis",
    "structures/fem/restrained-warping-torsion",
]

print("== existence check (planned) ==")
for c in candidates + reserve:
    p = os.path.join(ROOT, "skills", c)
    print(("EXISTS !!! " if os.path.isdir(p) else "ok        ") + c)

print("== standards map ids ==")
sm = open(os.path.join(ROOT, "standards-map.yaml"), encoding="utf-8").read()
ids = re.findall(r"(?m)^\s*- id:\s*(\S+)", sm)
print(f"total ids: {len(ids)}")
need = ["far-25","cs-25","far-29","ecss","far-33","rtca-do-229","arp4754a","naca-tr-824","mmpsd","arp4761a"]
for n in need:
    print(("present " if n in ids else "MISSING ") + n)
