"""Inorganic dyeing of an anodic coating to a black finish.

Anchor: ECSS-Q-ST-70-03C, process clause, dyeing (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Grade the dye chemistry. An inorganic black is produced in the pore
   rather than adsorbed on it: the coating is loaded with a metal salt
   in one bath and the pigment is precipitated in a second. Each bath
   carries a concentration, a pH and a temperature window, and the two
   baths are separated by a rinse so the precipitate forms inside the
   pore and not in the tank.
2. Bound the hold between the tank and the dye. A freshly anodized
   coating has open pores that close as it ages and dries, so the
   window from the anodizing rinse to the first dye bath is the single
   most-missed parameter on the line.
3. Turn the coating thickness into an immersion time. A deeper pore
   takes longer to load, so the time scales with the thickness above a
   floor that covers the surface itself.
4. Grade the colour. Solar absorptance is measured at several points,
   and the finish is accepted on the mean, on the spread between the
   points, and on the weakest single point, because a black that is
   black on average and grey in one corner is not a black finish.
5. Report findings, the colour statistics and one verdict.

Stdlib only, offline, deterministic.
"""

DYE_STEP_LOAD = "metal-salt-loading"
DYE_STEP_RINSE = "intermediate-rinse"
DYE_STEP_PRECIPITATE = "pigment-precipitation"
DYE_SEQUENCE = (DYE_STEP_LOAD, DYE_STEP_RINSE, DYE_STEP_PRECIPITATE)

# Bath windows, keyed by step.
BATH_WINDOWS = {
    DYE_STEP_LOAD: {
        "concentration_g_l": (20.0, 60.0),
        "ph": (4.5, 6.5),
        "temperature_c": (45.0, 65.0),
    },
    DYE_STEP_PRECIPITATE: {
        "concentration_g_l": (10.0, 40.0),
        "ph": (5.0, 7.0),
        "temperature_c": (40.0, 60.0),
    },
}

# Immersion time: a floor that covers the surface, plus a term that
# scales with the depth of pore to be loaded.
MIN_IMMERSION_MINUTES = 5.0
IMMERSION_MINUTES_PER_UM = 1.2

# Longest a coating may wait between the anodizing rinse and the first
# dye bath before the pores have closed too far to load evenly.
MAX_HOLD_MINUTES = 30.0

# Colour acceptance on solar absorptance.
MIN_MEAN_ABSORPTANCE = 0.90
MIN_POINT_ABSORPTANCE = 0.87
MAX_ABSORPTANCE_SPREAD = 0.04
MIN_COLOUR_POINTS = 3

# Absorptance figures are means of measured floats, so a lot sitting
# exactly on a bound can land a few units in the last place the wrong
# side of it. This tolerance is far below any reflectometer resolution
# and absorbs that representation error without relaxing the bound.
ABSORPTANCE_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return value


def required_immersion_minutes(coating_thickness_um):
    """Dye immersion time a coating thickness needs, in minutes."""
    thickness = _numeric("coating_thickness_um", coating_thickness_um, 0.0)
    scaled = IMMERSION_MINUTES_PER_UM * thickness
    return scaled if scaled > MIN_IMMERSION_MINUTES else MIN_IMMERSION_MINUTES


def check_bath(step, concentration_g_l, ph, temperature_c):
    """Findings about one dye bath against its own windows."""
    if step not in BATH_WINDOWS:
        raise ValueError(
            "unknown dye bath step %r (expected one of %s)"
            % (step, ", ".join(sorted(BATH_WINDOWS)))
        )
    window = BATH_WINDOWS[step]
    values = {
        "concentration_g_l": _numeric(
            "%s concentration_g_l" % step, concentration_g_l, 0.0
        ),
        "ph": _numeric("%s ph" % step, ph, 0.0, 14.0),
        "temperature_c": _numeric("%s temperature_c" % step, temperature_c),
    }
    findings = []
    for key, value in sorted(values.items()):
        low, high = window[key]
        if value < low:
            findings.append("%s-%s-below-window" % (step, key.replace("_", "-")))
        if value > high:
            findings.append("%s-%s-above-window" % (step, key.replace("_", "-")))
    return findings


def check_sequence(steps):
    """Findings about the order of the declared dye steps."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence")
    for step in steps:
        if step not in DYE_SEQUENCE:
            raise ValueError("unknown dye step %r" % (step,))
    steps = tuple(steps)
    findings = []
    for expected in DYE_SEQUENCE:
        if expected not in steps:
            findings.append("dye-step-missing-%s" % expected)
    present = [s for s in steps if s in DYE_SEQUENCE]
    ranks = [DYE_SEQUENCE.index(s) for s in present]
    if ranks != sorted(ranks):
        findings.append("dye-steps-out-of-order")
    return findings


def check_hold(hold_minutes):
    """Findings about the wait between the anodizing rinse and the dye."""
    minutes = _numeric("hold_minutes", hold_minutes, 0.0)
    if minutes > MAX_HOLD_MINUTES:
        return ["coating-held-too-long-before-dyeing"]
    return []


def check_immersion(immersion_minutes, coating_thickness_um):
    """Findings about the declared immersion time, plus the time needed."""
    declared = _numeric("immersion_minutes", immersion_minutes, 0.0)
    needed = required_immersion_minutes(coating_thickness_um)
    findings = []
    if declared + ABSORPTANCE_TOLERANCE < needed:
        findings.append("dye-immersion-shorter-than-the-coating-depth-needs")
    return findings, needed


def absorptance_statistics(readings):
    """Mean, minimum and spread of a set of solar-absorptance readings."""
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence")
    values = [
        _numeric("absorptance reading", value, 0.0, 1.0) for value in readings
    ]
    return {
        "count": len(values),
        "mean": sum(values) / len(values),
        "minimum": min(values),
        "maximum": max(values),
        "spread": max(values) - min(values),
    }


def colour_findings(readings):
    """Findings about colour acceptance, plus the statistics behind them."""
    stats = absorptance_statistics(readings)
    findings = []
    if stats["count"] < MIN_COLOUR_POINTS:
        findings.append("too-few-colour-measurement-points")
    if stats["mean"] + ABSORPTANCE_TOLERANCE < MIN_MEAN_ABSORPTANCE:
        findings.append("mean-absorptance-below-acceptance")
    if stats["minimum"] + ABSORPTANCE_TOLERANCE < MIN_POINT_ABSORPTANCE:
        findings.append("single-point-absorptance-below-acceptance")
    if stats["spread"] > MAX_ABSORPTANCE_SPREAD + ABSORPTANCE_TOLERANCE:
        findings.append("absorptance-spread-above-the-uniformity-limit")
    return findings, stats


def validate_dyeing_run(runrec):
    """Validate one dyeing run record and return a normalized copy."""
    if not isinstance(runrec, dict):
        raise ValueError("run must be a mapping")
    run_id = runrec.get("id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run needs a non-empty string id")
    steps = runrec.get("steps", list(DYE_SEQUENCE))
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("run %s needs a non-empty steps sequence" % run_id)
    baths = runrec.get("baths", {})
    if not isinstance(baths, dict):
        raise ValueError("run %s baths must be a mapping" % run_id)
    for key in baths:
        if key not in BATH_WINDOWS:
            raise ValueError("run %s declares unknown bath %r" % (run_id, key))
    readings = runrec.get("absorptance_readings", [])
    if not isinstance(readings, (list, tuple)):
        raise ValueError("run %s absorptance_readings must be a sequence" % run_id)
    return {
        "id": run_id.strip(),
        "steps": tuple(steps),
        "baths": dict(baths),
        "coating_thickness_um": _numeric(
            "run %s coating_thickness_um" % run_id,
            runrec.get("coating_thickness_um", 10.0),
            0.0,
        ),
        "immersion_minutes": _numeric(
            "run %s immersion_minutes" % run_id,
            runrec.get("immersion_minutes", 15.0),
            0.0,
        ),
        "hold_minutes": _numeric(
            "run %s hold_minutes" % run_id, runrec.get("hold_minutes", 10.0), 0.0
        ),
        "absorptance_readings": list(readings),
    }


def assess_dyeing(runrec):
    """Assess one dyeing run against the process clause."""
    norm = validate_dyeing_run(runrec)
    findings = list(check_sequence(norm["steps"]))
    for step in sorted(norm["baths"]):
        bath = norm["baths"][step]
        if not isinstance(bath, dict):
            raise ValueError("run %s bath %s must be a mapping" % (norm["id"], step))
        findings.extend(
            check_bath(
                step,
                bath.get("concentration_g_l", 0.0),
                bath.get("ph", 7.0),
                bath.get("temperature_c", 20.0),
            )
        )
    for step in BATH_WINDOWS:
        if step not in norm["baths"]:
            findings.append("no-bath-record-for-%s" % step)
    findings.extend(check_hold(norm["hold_minutes"]))
    immersion_findings, needed = check_immersion(
        norm["immersion_minutes"], norm["coating_thickness_um"]
    )
    findings.extend(immersion_findings)
    stats = None
    if norm["absorptance_readings"]:
        colour, stats = colour_findings(norm["absorptance_readings"])
        findings.extend(colour)
    else:
        findings.append("no-colour-measurement-on-record")
    return {
        "id": norm["id"],
        "required_immersion_minutes": needed,
        "colour": stats,
        "findings": findings,
        "compliant": not findings,
    }


def assess_dyeing_runs(runs):
    """Assess several dyeing runs together."""
    if not isinstance(runs, list) or not runs:
        raise ValueError("runs must be a non-empty list")
    results = []
    seen = set()
    for runrec in runs:
        result = assess_dyeing(runrec)
        if result["id"] in seen:
            raise ValueError("duplicate run id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    return {
        "runs": results,
        "non_compliant_ids": [r["id"] for r in results if not r["compliant"]],
        "compliant": all(r["compliant"] for r in results),
    }
