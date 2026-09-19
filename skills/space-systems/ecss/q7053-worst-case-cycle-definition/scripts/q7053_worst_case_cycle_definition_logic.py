"""Worst-case cycle definition for a sterilization compatibility test.

Anchor: the procedure clause of ECSS-Q-ST-70-53 that fixes the severity of the
compatibility test per sterilization method. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the campaign: cycle count and over-test factor.
2. Validate each process parameter: nominal value, tolerance, declared
   severity direction, whether the quantity accumulates, and the optional
   declared material capability.
3. Push each parameter to its worst corner along the severity direction.
4. Scale the cumulative parameters by the cycle count and the over-test
   factor; leave the instantaneous ones alone.
5. Compute a direction-aware margin against the declared capability, leaving
   it undefined when none was declared.
6. Identify the driving parameter and report the findings.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "SEVERITY_HIGH",
    "SEVERITY_LOW",
    "validate_campaign",
    "validate_parameter",
    "worst_corner",
    "scaled_level",
    "capability_margin",
    "derive_parameter",
    "driving_parameter",
    "assess_worst_case_cycle",
]

# A margin at exactly zero can land a few ULP either side; absorb the
# representation error rather than moving the declared capability.
MARGIN_TOLERANCE = 1e-9

SEVERITY_HIGH = "high"
SEVERITY_LOW = "low"
_DIRECTIONS = (SEVERITY_HIGH, SEVERITY_LOW)


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def validate_campaign(cycle_count, over_test_factor):
    """Return the validated (cycle_count, over_test_factor) pair."""
    if not isinstance(cycle_count, int) or isinstance(cycle_count, bool):
        raise ValueError("cycle_count must be an integer")
    if cycle_count < 1:
        raise ValueError("cycle_count must be at least 1, got %d" % cycle_count)
    factor = _real(over_test_factor, "over_test_factor")
    if factor < 1.0:
        raise ValueError(
            "over_test_factor %g would define a test weaker than the process" % factor
        )
    return (cycle_count, factor)


def validate_parameter(parameter):
    """Return a validated process parameter record.

    Keys: name, nominal, tolerance, direction, cumulative; optional capability.
    """
    if not isinstance(parameter, dict):
        raise ValueError("parameter must be a mapping")
    for key in ("name", "nominal", "tolerance", "direction", "cumulative"):
        if key not in parameter:
            raise ValueError("parameter missing required key '%s'" % key)
    name = parameter["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("parameter name must be a non-empty string")
    direction = parameter["direction"]
    if direction not in _DIRECTIONS:
        raise ValueError(
            "parameter %s direction must be one of %s, got %r"
            % (name, ", ".join(_DIRECTIONS), direction)
        )
    cumulative = parameter["cumulative"]
    if not isinstance(cumulative, bool):
        raise ValueError("parameter %s cumulative must be a boolean" % name)
    tolerance = _real(parameter["tolerance"], "parameter %s tolerance" % name)
    if tolerance < 0.0:
        raise ValueError("parameter %s tolerance must not be negative" % name)
    capability = parameter.get("capability")
    if capability is not None:
        capability = _real(capability, "parameter %s capability" % name)
        if capability == 0.0:
            raise ValueError("parameter %s capability must not be zero" % name)
    return {
        "name": name.strip(),
        "nominal": _real(parameter["nominal"], "parameter %s nominal" % name),
        "tolerance": tolerance,
        "direction": direction,
        "cumulative": cumulative,
        "capability": capability,
    }


def worst_corner(nominal, tolerance, direction):
    """Return the nominal value pushed to its worst corner."""
    if direction not in _DIRECTIONS:
        raise ValueError("direction must be one of %s" % ", ".join(_DIRECTIONS))
    value = _real(nominal, "nominal")
    band = _real(tolerance, "tolerance")
    if band < 0.0:
        raise ValueError("tolerance must not be negative")
    return value + band if direction == SEVERITY_HIGH else value - band


def scaled_level(corner, cumulative, cycle_count, over_test_factor):
    """Return the corner scaled for the campaign when the quantity accumulates."""
    if not isinstance(cumulative, bool):
        raise ValueError("cumulative must be a boolean")
    count, factor = validate_campaign(cycle_count, over_test_factor)
    value = _real(corner, "corner")
    if not cumulative:
        return value
    return value * count * factor


def capability_margin(level, capability, direction):
    """Return the unused fraction of capability, in the sense of the direction.

    None is returned when no capability was declared. Positive is headroom,
    zero is exactly at capability, negative is a shortfall.
    """
    if capability is None:
        return None
    if direction not in _DIRECTIONS:
        raise ValueError("direction must be one of %s" % ", ".join(_DIRECTIONS))
    applied = _real(level, "level")
    limit = _real(capability, "capability")
    if limit == 0.0:
        raise ValueError("capability must not be zero")
    if direction == SEVERITY_HIGH:
        return (limit - applied) / abs(limit)
    return (applied - limit) / abs(limit)


def derive_parameter(parameter, cycle_count, over_test_factor):
    """Return the derived worst-case level and margin for one parameter."""
    record = validate_parameter(parameter)
    corner = worst_corner(record["nominal"], record["tolerance"], record["direction"])
    level = scaled_level(corner, record["cumulative"], cycle_count, over_test_factor)
    margin = capability_margin(level, record["capability"], record["direction"])
    return {
        "name": record["name"],
        "nominal": record["nominal"],
        "tolerance": record["tolerance"],
        "direction": record["direction"],
        "cumulative": record["cumulative"],
        "worst_corner": corner,
        "worst_case_level": level,
        "capability": record["capability"],
        "margin": margin,
        "within_capability": None if margin is None else margin >= -MARGIN_TOLERANCE,
    }


def driving_parameter(records):
    """Return the record with the least declared margin, or None when none is."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    driver = None
    for record in records:
        if not isinstance(record, dict) or "margin" not in record or "name" not in record:
            raise ValueError("each record must carry 'margin' and 'name'")
        if record["margin"] is None:
            continue
        if driver is None:
            driver = record
            continue
        if math.isclose(record["margin"], driver["margin"], rel_tol=1e-12, abs_tol=0.0):
            if record["name"] < driver["name"]:
                driver = record
        elif record["margin"] < driver["margin"]:
            driver = record
    return driver


def assess_worst_case_cycle(spec):
    """Derive the worst-case cycle for one sterilization method.

    spec keys: method, parameters, cycle_count, over_test_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("method", "parameters", "cycle_count", "over_test_factor"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    method = spec["method"]
    if not isinstance(method, str) or not method.strip():
        raise ValueError("method must be a non-empty string")
    parameters = spec["parameters"]
    if not isinstance(parameters, (list, tuple)) or not parameters:
        raise ValueError("parameters must be a non-empty sequence")
    count, factor = validate_campaign(spec["cycle_count"], spec["over_test_factor"])
    records = [derive_parameter(item, count, factor) for item in parameters]
    seen = set()
    for record in records:
        if record["name"] in seen:
            raise ValueError("duplicated parameter name %r" % record["name"])
        seen.add(record["name"])
    driver = driving_parameter(records)
    findings = []
    for record in records:
        if record["capability"] is None:
            findings.append(
                "parameter %s has no declared material capability; its margin is undefined"
                % record["name"]
            )
        elif not record["within_capability"]:
            findings.append(
                "worst-case %s of %.6f exceeds the declared capability %.6f "
                "(margin %.6f)"
                % (record["name"], record["worst_case_level"], record["capability"],
                   record["margin"])
            )
    return {
        "method": method.strip(),
        "cycle_count": count,
        "over_test_factor": factor,
        "parameters": records,
        "driving_parameter": None if driver is None else driver["name"],
        "least_margin": None if driver is None else driver["margin"],
        "acceptable": not findings,
        "findings": findings,
    }
