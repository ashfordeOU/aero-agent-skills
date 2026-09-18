"""Bath chemical control and analysis scheduling for a black-anodizing line.

Anchor: ECSS-Q-ST-70-03C, process-control clause (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Every tank on the line carries a parameter set, and every parameter
   carries a nominal value, a control band and a reject band. Inside
   the control band the tank runs; between the control and reject
   bands it runs after an addition; outside the reject band it comes
   off line, because a part run through it cannot be recovered by
   anything done later.
2. Analysis is scheduled on two clocks at once: elapsed time since the
   last analysis, and the part area processed since then. Whichever
   arrives first makes the analysis due, because a tank ages while it
   idles and also while it works.
3. An addition is a quantity, not an instruction. For a parameter
   below nominal the correction follows from the tank volume, the
   shortfall and the strength of the addition being made, and it is
   reported in the units the operator will weigh out.
4. A parameter that has drifted above nominal cannot be added to. It
   is corrected by dilution, and the dilution volume follows from the
   same arithmetic run the other way.
5. The line is in control only when every tank is, so the line
   disposition is the worst tank disposition, and an overdue analysis
   is a finding in its own right rather than a reason to trust the
   last reading.

Stdlib only, offline, deterministic.
"""

IN_CONTROL = "in-control"
ADJUST = "adjustment-required"
OUT_OF_SERVICE = "out-of-service"

_RANK = {IN_CONTROL: 0, ADJUST: 1, OUT_OF_SERVICE: 2}

# Analysis schedule per tank: elapsed hours, and processed area in
# square decimetres. Whichever is reached first makes the analysis due.
ANALYSIS_SCHEDULE = {
    "alkaline-cleaner": {"interval_hours": 168.0, "interval_area_dm2": 4000.0},
    "alkaline-etch": {"interval_hours": 72.0, "interval_area_dm2": 2000.0},
    "deoxidizer": {"interval_hours": 72.0, "interval_area_dm2": 2000.0},
    "anodizing-electrolyte": {"interval_hours": 24.0, "interval_area_dm2": 1000.0},
    "dye-bath": {"interval_hours": 48.0, "interval_area_dm2": 1500.0},
    "seal-bath": {"interval_hours": 48.0, "interval_area_dm2": 1500.0},
}

VALID_TANKS = tuple(sorted(ANALYSIS_SCHEDULE))

# An analysis this far past its due point takes the tank off line
# rather than merely flagging it, as a fraction of the interval.
OVERDUE_GRACE_FRACTION = 0.5

# Concentrations are quotients of measured floats, so a tank sitting
# exactly on a band edge can land a few units in the last place outside
# it. A nanogram per litre is far below any titration resolution and
# absorbs that representation error without widening the band.
CONCENTRATION_TOLERANCE_G_L = 1.0e-9


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def validate_parameter(parameter):
    """Validate one parameter record and return a normalized copy."""
    if not isinstance(parameter, dict):
        raise ValueError("parameter must be a mapping")
    name = parameter.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("parameter needs a non-empty string name")
    nominal = _numeric("%s nominal" % name, parameter.get("nominal"))
    control_low = _numeric("%s control_low" % name, parameter.get("control_low"))
    control_high = _numeric("%s control_high" % name, parameter.get("control_high"))
    reject_low = _numeric("%s reject_low" % name, parameter.get("reject_low"))
    reject_high = _numeric("%s reject_high" % name, parameter.get("reject_high"))
    if not reject_low <= control_low <= control_high <= reject_high:
        raise ValueError(
            "%s bands must nest reject_low <= control_low <= control_high "
            "<= reject_high" % name
        )
    if not control_low <= nominal <= control_high:
        raise ValueError("%s nominal must sit inside its control band" % name)
    return {
        "name": name.strip(),
        "nominal": nominal,
        "control_low": control_low,
        "control_high": control_high,
        "reject_low": reject_low,
        "reject_high": reject_high,
        "measured": _numeric("%s measured" % name, parameter.get("measured")),
    }


def parameter_disposition(parameter):
    """Disposition one parameter forces on its tank."""
    norm = validate_parameter(parameter)
    value = norm["measured"]
    if value < norm["reject_low"] - CONCENTRATION_TOLERANCE_G_L:
        return OUT_OF_SERVICE
    if value > norm["reject_high"] + CONCENTRATION_TOLERANCE_G_L:
        return OUT_OF_SERVICE
    if value < norm["control_low"] - CONCENTRATION_TOLERANCE_G_L:
        return ADJUST
    if value > norm["control_high"] + CONCENTRATION_TOLERANCE_G_L:
        return ADJUST
    return IN_CONTROL


def addition_mass_kg(volume_l, shortfall_g_l, additive_strength_fraction=1.0):
    """Mass of additive that raises a tank by a shortfall, in kilograms."""
    volume = _numeric("volume_l", volume_l, 0.0)
    if volume <= 0.0:
        raise ValueError("volume_l must be positive")
    shortfall = _numeric("shortfall_g_l", shortfall_g_l, 0.0)
    strength = _numeric("additive_strength_fraction", additive_strength_fraction, 0.0)
    if strength <= 0.0 or strength > 1.0:
        raise ValueError("additive_strength_fraction must lie in (0, 1]")
    return volume * shortfall / (1000.0 * strength)


def dilution_volume_l(volume_l, measured_g_l, target_g_l):
    """Make-up volume that dilutes a tank back to its target, in litres."""
    volume = _numeric("volume_l", volume_l, 0.0)
    if volume <= 0.0:
        raise ValueError("volume_l must be positive")
    measured = _numeric("measured_g_l", measured_g_l, 0.0)
    target = _numeric("target_g_l", target_g_l, 0.0)
    if target <= 0.0:
        raise ValueError("target_g_l must be positive")
    if measured <= target:
        return 0.0
    return volume * (measured - target) / target


def correction_for(parameter, volume_l, additive_strength_fraction=1.0):
    """Correction one parameter needs, as an addition or a dilution."""
    norm = validate_parameter(parameter)
    disposition = parameter_disposition(norm)
    if disposition == IN_CONTROL:
        return {"action": "none", "addition_kg": 0.0, "dilution_l": 0.0}
    if norm["measured"] < norm["nominal"]:
        shortfall = norm["nominal"] - norm["measured"]
        return {
            "action": "addition",
            "addition_kg": addition_mass_kg(
                volume_l, shortfall, additive_strength_fraction
            ),
            "dilution_l": 0.0,
        }
    return {
        "action": "dilution",
        "addition_kg": 0.0,
        "dilution_l": dilution_volume_l(volume_l, norm["measured"], norm["nominal"]),
    }


def analysis_status(tank, hours_since_analysis, area_since_analysis_dm2):
    """Whether an analysis is due or overdue on either of the two clocks."""
    if tank not in ANALYSIS_SCHEDULE:
        raise ValueError(
            "unknown tank %r (expected one of %s)" % (tank, ", ".join(VALID_TANKS))
        )
    schedule = ANALYSIS_SCHEDULE[tank]
    hours = _numeric("hours_since_analysis", hours_since_analysis, 0.0)
    area = _numeric("area_since_analysis_dm2", area_since_analysis_dm2, 0.0)
    hour_fraction = hours / schedule["interval_hours"]
    area_fraction = area / schedule["interval_area_dm2"]
    worst = hour_fraction if hour_fraction > area_fraction else area_fraction
    driver = "elapsed-time" if hour_fraction > area_fraction else "processed-area"
    if worst > 1.0 + OVERDUE_GRACE_FRACTION:
        state = "overdue"
    elif worst > 1.0:
        state = "due"
    else:
        state = "current"
    return {"state": state, "driver": driver, "fraction_of_interval": worst}


def validate_tank(tank_record):
    """Validate one tank record and return a normalized copy."""
    if not isinstance(tank_record, dict):
        raise ValueError("tank must be a mapping")
    tank = tank_record.get("tank")
    if tank not in ANALYSIS_SCHEDULE:
        raise ValueError("unknown tank %r" % (tank,))
    parameters = tank_record.get("parameters", [])
    if not isinstance(parameters, (list, tuple)) or not parameters:
        raise ValueError("tank %s needs a non-empty parameters sequence" % tank)
    normalized = [validate_parameter(p) for p in parameters]
    names = [p["name"] for p in normalized]
    if len(set(names)) != len(names):
        raise ValueError("tank %s repeats a parameter name" % tank)
    return {
        "tank": tank,
        "volume_l": _numeric(
            "tank %s volume_l" % tank, tank_record.get("volume_l", 1000.0), 0.0
        ),
        "hours_since_analysis": _numeric(
            "tank %s hours_since_analysis" % tank,
            tank_record.get("hours_since_analysis", 0.0),
            0.0,
        ),
        "area_since_analysis_dm2": _numeric(
            "tank %s area_since_analysis_dm2" % tank,
            tank_record.get("area_since_analysis_dm2", 0.0),
            0.0,
        ),
        "additive_strength_fraction": _numeric(
            "tank %s additive_strength_fraction" % tank,
            tank_record.get("additive_strength_fraction", 1.0),
            0.0,
        ),
        "parameters": normalized,
    }


def assess_tank(tank_record):
    """Assess one tank: disposition, corrections and analysis status."""
    norm = validate_tank(tank_record)
    disposition = IN_CONTROL
    findings = []
    corrections = []
    for parameter in norm["parameters"]:
        param_disposition = parameter_disposition(parameter)
        if _RANK[param_disposition] > _RANK[disposition]:
            disposition = param_disposition
        if param_disposition == OUT_OF_SERVICE:
            findings.append("%s-outside-its-reject-band" % parameter["name"])
        elif param_disposition == ADJUST:
            findings.append("%s-outside-its-control-band" % parameter["name"])
        correction = correction_for(
            parameter, norm["volume_l"], norm["additive_strength_fraction"]
        )
        if correction["action"] != "none":
            correction["parameter"] = parameter["name"]
            corrections.append(correction)
    analysis = analysis_status(
        norm["tank"], norm["hours_since_analysis"], norm["area_since_analysis_dm2"]
    )
    if analysis["state"] == "due":
        findings.append("analysis-due-on-%s" % analysis["driver"])
        if _RANK[ADJUST] > _RANK[disposition]:
            disposition = ADJUST
    elif analysis["state"] == "overdue":
        findings.append("analysis-overdue-on-%s" % analysis["driver"])
        disposition = OUT_OF_SERVICE
    return {
        "tank": norm["tank"],
        "disposition": disposition,
        "analysis": analysis,
        "corrections": corrections,
        "findings": findings,
    }


def assess_line(tanks):
    """Assess every tank on the line and report the line disposition."""
    if not isinstance(tanks, list) or not tanks:
        raise ValueError("tanks must be a non-empty list")
    results = []
    seen = set()
    for tank_record in tanks:
        result = assess_tank(tank_record)
        if result["tank"] in seen:
            raise ValueError("duplicate tank %r" % (result["tank"],))
        seen.add(result["tank"])
        results.append(result)
    line = IN_CONTROL
    for result in results:
        if _RANK[result["disposition"]] > _RANK[line]:
            line = result["disposition"]
    return {
        "tanks": results,
        "line_disposition": line,
        "tanks_out_of_service": [
            r["tank"] for r in results if r["disposition"] == OUT_OF_SERVICE
        ],
        "analysis_due_tanks": [
            r["tank"] for r in results if r["analysis"]["state"] != "current"
        ],
    }
