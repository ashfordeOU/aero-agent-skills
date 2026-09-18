"""Sealing a dyed black anodic coating.

Anchor: ECSS-Q-ST-70-03C, process clause, sealing (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Pick the method and hold it to its own window. Hot-water sealing
   hydrates the coating and closes the pores from the inside;
   nickel-acetate sealing precipitates a hydroxide in the pore mouth
   and works cooler and faster. Each carries its own temperature band,
   its own time constant and, for the acetate route, a concentration
   and pH window of its own.
2. Turn the coating thickness into a sealing time. A deeper pore takes
   longer to close, so the time scales with the thickness above a
   floor, and the floor differs by method.
3. Grade the water. Sealing is a hydration reaction and the ions in
   the water take part in it. Conductivity above the limit, silicate
   or phosphate present at all, and the seal is poisoned while the
   tank temperature and time look perfect.
4. Bound the hold between the dye and the seal, because an unsealed
   dyed coating bleeds colour and picks up contamination until it is
   closed.
5. Grade the result. Absorptance lost across the seal measures dye
   pulled back out; a bleed rating measures what a wipe takes off.
6. Report findings, the required time and one verdict.

Stdlib only, offline, deterministic.
"""

METHOD_HOT_WATER = "hot-water"
METHOD_NICKEL_ACETATE = "nickel-acetate"
VALID_METHODS = (METHOD_HOT_WATER, METHOD_NICKEL_ACETATE)

# Per-method temperature band, time floor and time per micrometre.
METHOD_WINDOWS = {
    METHOD_HOT_WATER: {
        "temperature_c": (96.0, 100.0),
        "floor_minutes": 15.0,
        "minutes_per_um": 2.5,
    },
    METHOD_NICKEL_ACETATE: {
        "temperature_c": (80.0, 90.0),
        "floor_minutes": 10.0,
        "minutes_per_um": 1.5,
    },
}

# Nickel-acetate bath chemistry.
MIN_NICKEL_ACETATE_G_L = 5.0
MAX_NICKEL_ACETATE_G_L = 8.0
MIN_SEAL_PH = 5.5
MAX_SEAL_PH = 6.5

# Water quality. Conductivity is a ceiling; the two poisons are
# reported at any declared presence.
MAX_CONDUCTIVITY_US_CM = 30.0
MAX_SILICATE_MG_L = 0.5
MAX_PHOSPHATE_MG_L = 0.5

# Longest a dyed but unsealed coating may wait, in minutes.
MAX_DYE_TO_SEAL_MINUTES = 20.0

# Acceptance on the seal result.
MAX_ABSORPTANCE_LOSS = 0.02
MAX_BLEED_RATING = 1

# Times and absorptance differences are built from measured floats, so
# a lot sitting exactly on a bound can land a few units in the last
# place the wrong side of it. These tolerances sit far below any shop
# instrument and absorb that representation error without relaxing the
# bounds themselves.
TIME_TOLERANCE_MINUTES = 1.0e-9
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


def _method(method):
    if method not in VALID_METHODS:
        raise ValueError(
            "method must be one of %s, got %r" % (", ".join(VALID_METHODS), method)
        )
    return method


def required_seal_minutes(method, coating_thickness_um):
    """Sealing time a coating needs by the chosen method, in minutes."""
    window = METHOD_WINDOWS[_method(method)]
    thickness = _numeric("coating_thickness_um", coating_thickness_um, 0.0)
    scaled = window["minutes_per_um"] * thickness
    floor = window["floor_minutes"]
    return scaled if scaled > floor else floor


def check_temperature(method, temperature_c):
    """Findings about the seal-tank temperature for the chosen method."""
    low, high = METHOD_WINDOWS[_method(method)]["temperature_c"]
    temperature = _numeric("temperature_c", temperature_c)
    findings = []
    if temperature < low:
        findings.append("seal-temperature-below-the-%s-window" % method)
    if temperature > high:
        findings.append("seal-temperature-above-the-%s-window" % method)
    return findings


def check_seal_time(method, declared_minutes, coating_thickness_um):
    """Findings about the declared seal time, plus the time needed."""
    needed = required_seal_minutes(method, coating_thickness_um)
    declared = _numeric("declared_minutes", declared_minutes, 0.0)
    findings = []
    if declared + TIME_TOLERANCE_MINUTES < needed:
        findings.append("seal-time-shorter-than-the-coating-depth-needs")
    return findings, needed


def check_water(conductivity_us_cm, silicate_mg_l, phosphate_mg_l):
    """Findings about the quality of the sealing water."""
    conductivity = _numeric("conductivity_us_cm", conductivity_us_cm, 0.0)
    silicate = _numeric("silicate_mg_l", silicate_mg_l, 0.0)
    phosphate = _numeric("phosphate_mg_l", phosphate_mg_l, 0.0)
    findings = []
    if conductivity > MAX_CONDUCTIVITY_US_CM:
        findings.append("seal-water-conductivity-above-the-limit")
    if silicate > MAX_SILICATE_MG_L:
        findings.append("silicate-in-the-seal-water-poisons-the-seal")
    if phosphate > MAX_PHOSPHATE_MG_L:
        findings.append("phosphate-in-the-seal-water-poisons-the-seal")
    return findings


def check_bath_chemistry(method, nickel_acetate_g_l, ph):
    """Findings about the seal-bath chemistry for the chosen method."""
    _method(method)
    value = _numeric("ph", ph, 0.0, 14.0)
    findings = []
    if value < MIN_SEAL_PH:
        findings.append("seal-bath-ph-below-window")
    if value > MAX_SEAL_PH:
        findings.append("seal-bath-ph-above-window")
    if method == METHOD_NICKEL_ACETATE:
        concentration = _numeric("nickel_acetate_g_l", nickel_acetate_g_l, 0.0)
        if concentration < MIN_NICKEL_ACETATE_G_L:
            findings.append("nickel-acetate-concentration-below-window")
        if concentration > MAX_NICKEL_ACETATE_G_L:
            findings.append("nickel-acetate-concentration-above-window")
    return findings


def check_dye_to_seal_hold(hold_minutes):
    """Findings about the wait between the dye and the seal tank."""
    minutes = _numeric("hold_minutes", hold_minutes, 0.0)
    if minutes > MAX_DYE_TO_SEAL_MINUTES:
        return ["dyed-coating-held-too-long-before-sealing"]
    return []


def absorptance_loss(before, after):
    """Absorptance given up across the seal, as a non-negative number."""
    start = _numeric("before", before, 0.0, 1.0)
    end = _numeric("after", after, 0.0, 1.0)
    loss = start - end
    return loss if loss > 0.0 else 0.0


def check_seal_result(before, after, bleed_rating):
    """Findings about the sealed result, plus the absorptance given up."""
    loss = absorptance_loss(before, after)
    if not isinstance(bleed_rating, int) or isinstance(bleed_rating, bool):
        raise ValueError("bleed_rating must be an integer, got %r" % (bleed_rating,))
    if bleed_rating < 0:
        raise ValueError("bleed_rating must be non-negative")
    findings = []
    if loss > MAX_ABSORPTANCE_LOSS + ABSORPTANCE_TOLERANCE:
        findings.append("absorptance-lost-across-the-seal-above-acceptance")
    if bleed_rating > MAX_BLEED_RATING:
        findings.append("dye-bleed-rating-above-acceptance")
    return findings, loss


def validate_seal_run(runrec):
    """Validate one sealing run record and return a normalized copy."""
    if not isinstance(runrec, dict):
        raise ValueError("run must be a mapping")
    run_id = runrec.get("id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run needs a non-empty string id")
    method = _method(runrec.get("method", METHOD_HOT_WATER))
    bleed = runrec.get("bleed_rating", 0)
    if not isinstance(bleed, int) or isinstance(bleed, bool) or bleed < 0:
        raise ValueError("run %s bleed_rating must be a non-negative integer" % run_id)
    return {
        "id": run_id.strip(),
        "method": method,
        "coating_thickness_um": _numeric(
            "run %s coating_thickness_um" % run_id,
            runrec.get("coating_thickness_um", 10.0),
            0.0,
        ),
        "temperature_c": _numeric(
            "run %s temperature_c" % run_id,
            runrec.get("temperature_c", METHOD_WINDOWS[method]["temperature_c"][0]),
        ),
        "declared_minutes": _numeric(
            "run %s declared_minutes" % run_id,
            runrec.get("declared_minutes", 30.0),
            0.0,
        ),
        "conductivity_us_cm": _numeric(
            "run %s conductivity_us_cm" % run_id,
            runrec.get("conductivity_us_cm", 10.0),
            0.0,
        ),
        "silicate_mg_l": _numeric(
            "run %s silicate_mg_l" % run_id, runrec.get("silicate_mg_l", 0.0), 0.0
        ),
        "phosphate_mg_l": _numeric(
            "run %s phosphate_mg_l" % run_id, runrec.get("phosphate_mg_l", 0.0), 0.0
        ),
        "nickel_acetate_g_l": _numeric(
            "run %s nickel_acetate_g_l" % run_id,
            runrec.get("nickel_acetate_g_l", 6.0),
            0.0,
        ),
        "ph": _numeric("run %s ph" % run_id, runrec.get("ph", 6.0), 0.0, 14.0),
        "hold_minutes": _numeric(
            "run %s hold_minutes" % run_id, runrec.get("hold_minutes", 5.0), 0.0
        ),
        "absorptance_before": _numeric(
            "run %s absorptance_before" % run_id,
            runrec.get("absorptance_before", 0.93),
            0.0,
            1.0,
        ),
        "absorptance_after": _numeric(
            "run %s absorptance_after" % run_id,
            runrec.get("absorptance_after", 0.92),
            0.0,
            1.0,
        ),
        "bleed_rating": bleed,
    }


def assess_sealing(runrec):
    """Assess one sealing run against the process clause."""
    norm = validate_seal_run(runrec)
    findings = []
    findings.extend(check_temperature(norm["method"], norm["temperature_c"]))
    time_findings, needed = check_seal_time(
        norm["method"], norm["declared_minutes"], norm["coating_thickness_um"]
    )
    findings.extend(time_findings)
    findings.extend(
        check_water(
            norm["conductivity_us_cm"],
            norm["silicate_mg_l"],
            norm["phosphate_mg_l"],
        )
    )
    findings.extend(
        check_bath_chemistry(norm["method"], norm["nickel_acetate_g_l"], norm["ph"])
    )
    findings.extend(check_dye_to_seal_hold(norm["hold_minutes"]))
    result_findings, loss = check_seal_result(
        norm["absorptance_before"], norm["absorptance_after"], norm["bleed_rating"]
    )
    findings.extend(result_findings)
    return {
        "id": norm["id"],
        "method": norm["method"],
        "required_seal_minutes": needed,
        "absorptance_loss": loss,
        "findings": findings,
        "compliant": not findings,
    }


def assess_sealing_runs(runs):
    """Assess several sealing runs together."""
    if not isinstance(runs, list) or not runs:
        raise ValueError("runs must be a non-empty list")
    results = []
    seen = set()
    for runrec in runs:
        result = assess_sealing(runrec)
        if result["id"] in seen:
            raise ValueError("duplicate run id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    return {
        "runs": results,
        "non_compliant_ids": [r["id"] for r in results if not r["compliant"]],
        "compliant": all(r["compliant"] for r in results),
    }
