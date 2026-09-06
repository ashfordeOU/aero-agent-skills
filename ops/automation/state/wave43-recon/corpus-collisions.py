#!/usr/bin/env python3
"""Wave-43 corpus collision probe: count occurrences of leaf-distinctive
tokens in eval/hit1-corpus.yaml. Leaves planned for wave-43 must have ~0
prior corpus tasks carrying their distinctive tokens (else new tasks could
collide / existing tasks could be stolen)."""
import os, sys

ROOT = os.path.expanduser("~/AeroSkills")
corpus = open(os.path.join(ROOT, "eval", "hit1-corpus.yaml"), encoding="utf-8").read().lower()

groups = {
    "batch-A": {
        "vmu-determination": ["vmu", "minimum unstick", "unstick speed", "rotation limit speed"],
        "rotorcraft-forward-flight-climb-test": ["forward flight climb", "best rate of climb rotorcraft", "rotorcraft climb flight test"],
        "rotorcraft-height-velocity-diagram-test": ["height velocity diagram", "dead man", "hv diagram", "height velocity demonstration"],
        "rocket-nozzle-divergence-loss": ["nozzle divergence", "conical nozzle", "bell contour", "divergence loss"],
    },
    "batch-B": {
        "turbofan-design-point": ["turbofan design point", "two spool", "fan stream station", "separate exhaust cycle", "design point turbofan"],
        "gnss-doppler-velocity-positioning": ["doppler positioning", "receiver velocity", "clock drift estimate", "delta range rate"],
        "process-noise-discretization": ["van loan", "process noise discret", "continuous spectral density", "discrete noise covariance"],
        "imu-static-calibration": ["six position", "rate table calibration", "imu calibration", "accelerometer bias scale"],
    },
    "batch-C": {
        "tightly-coupled-ins-gnss": ["tightly coupled", "raw pseudorange", "clock state filter"],
        "fanno-flow": ["fanno", "fanno line", "friction duct", "choking length"],
        "rayleigh-flow": ["rayleigh flow", "heat addition duct", "thermal choking", "rayleigh line"],
        "unsteady-laminar-stokes-layers": ["stokes first", "stokes second", "oscillating plate", "rayleigh layer", "impulsively started"],
    },
    "batch-D": {
        "crippling-analysis": ["crippling", "inter rivet buckling", "shape constant"],
        "hertzian-contact-stress": ["hertzian", "hertz contact", "contact patch"],
        "metallic-fastener-joints": ["bolt group", "eccentric bolt", "double shear", "net section"],
        "plastic-collapse-analysis": ["plastic hinge", "plastic collapse", "shape factor", "collapse load", "fully plastic"],
    },
}

which = sys.argv[1] if len(sys.argv) > 1 else "all"
for bname, leaves in groups.items():
    if which not in ("all", bname):
        continue
    print(f"==== {bname} ====")
    for leaf, toks in leaves.items():
        for t in toks:
            print(f"  {leaf}: '{t}' -> {corpus.count(t)}")
