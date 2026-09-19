"""Functional verification of an assembly at the temperature extremes of a test.

Anchor: ECSS-Q-ST-70-04C, the clauses requiring that an assembly be exercised
functionally while it is at the temperature extremes of the test, not only
before and after it. Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Build the set of check points the campaign owes: an ambient reference
   before, both extremes of the first and last cycle, both extremes of any
   declared intermediate cycle, and an ambient reference after.
2. Match the checks actually performed against that set and name the omissions
   and the checks that belong to no required point.
3. Confirm each performed check was taken with the item at the condition it
   claims, inside the tolerance band around that condition's temperature.
4. Judge every measured parameter of every check against its limits.
5. Compare the two ambient references parameter by parameter and report any
   relative drift beyond what the campaign allows.
6. Return one verification verdict with the findings behind it.
"""

import math

__all__ = [
    "CONDITIONS",
    "EXTREME_CONDITIONS",
    "COMPARISON_TOLERANCE",
    "required_check_points",
    "check_key",
    "index_checks",
    "coverage",
    "condition_temperature",
    "check_at_condition",
    "parameter_verdicts",
    "relative_drift",
    "ambient_drift",
    "assess_functional_verification",
]

# The conditions a functional check can be taken at.
CONDITIONS = ("ambient-pre", "cold-extreme", "hot-extreme", "ambient-post")

# The two that are at temperature; these are the ones the clause exists for.
EXTREME_CONDITIONS = ("cold-extreme", "hot-extreme")

# Temperatures, limits and drift fractions are floats; a value sitting on a
# bound is compared within this tolerance rather than by moving the bound.
COMPARISON_TOLERANCE = 1e-9


def _as_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _as_float(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def required_check_points(cycle_count, intermediate_every=None):
    """Return the check points the campaign owes, in the order they happen."""
    if not isinstance(cycle_count, int) or isinstance(cycle_count, bool):
        raise ValueError("cycle_count must be an integer")
    if cycle_count < 1:
        raise ValueError("cycle_count must be at least 1, got %d" % cycle_count)
    if intermediate_every is not None:
        if not isinstance(intermediate_every, int) or isinstance(intermediate_every, bool):
            raise ValueError("intermediate_every must be an integer or None")
        if intermediate_every < 1:
            raise ValueError("intermediate_every must be at least 1")
    cycles = set([1, cycle_count])
    if intermediate_every is not None:
        cycle = intermediate_every
        while cycle <= cycle_count:
            cycles.add(cycle)
            cycle += intermediate_every
    points = [{"condition": "ambient-pre", "cycle": 0}]
    for cycle in sorted(cycles):
        for condition in EXTREME_CONDITIONS:
            points.append({"condition": condition, "cycle": cycle})
    points.append({"condition": "ambient-post", "cycle": cycle_count + 1})
    return points


def check_key(point):
    """Return the (condition, cycle) key identifying one check point."""
    if not isinstance(point, dict):
        raise ValueError("check point must be a mapping")
    for key in ("condition", "cycle"):
        if key not in point:
            raise ValueError("check point missing required key '%s'" % key)
    condition = point["condition"]
    if condition not in CONDITIONS:
        raise ValueError(
            "unknown condition %r, expected one of %s" % (condition, ", ".join(CONDITIONS))
        )
    cycle = point["cycle"]
    if not isinstance(cycle, int) or isinstance(cycle, bool):
        raise ValueError("check point cycle must be an integer")
    if cycle < 0:
        raise ValueError("check point cycle must be non-negative, got %d" % cycle)
    return (condition, cycle)


def index_checks(checks):
    """Return the performed checks keyed by (condition, cycle)."""
    if not isinstance(checks, (list, tuple)):
        raise ValueError("checks must be a sequence")
    indexed = {}
    for check in checks:
        key = check_key(check)
        if key in indexed:
            raise ValueError("duplicate check for condition %s of cycle %d" % key)
        indexed[key] = check
    return indexed


def coverage(required, performed):
    """Return the required points with no check, and the checks with no point."""
    required_keys = [check_key(point) for point in required]
    performed_keys = set(performed)
    missing = [key for key in required_keys if key not in performed_keys]
    unscheduled = sorted(key for key in performed_keys if key not in set(required_keys))
    return {
        "required": required_keys,
        "missing": missing,
        "unscheduled": unscheduled,
        "complete": not missing,
    }


def condition_temperature(condition, temperatures):
    """Return the temperature a check at this condition should have been taken at."""
    if condition not in CONDITIONS:
        raise ValueError("unknown condition %r" % (condition,))
    if not isinstance(temperatures, dict):
        raise ValueError("temperatures must be a mapping of condition to celsius")
    if condition not in temperatures:
        raise ValueError("no target temperature declared for condition '%s'" % condition)
    return _as_float(temperatures[condition], "target temperature for %s" % condition)


def check_at_condition(check, temperatures, band_k):
    """Judge whether a check was taken with the item at the condition it claims."""
    condition, cycle = check_key(check)
    if "temperature_c" not in check:
        raise ValueError("check for %s of cycle %d carries no temperature_c" % (condition, cycle))
    band = _positive(band_k, "band_k")
    measured = _as_float(check["temperature_c"], "temperature_c")
    target = condition_temperature(condition, temperatures)
    deviation = abs(measured - target)
    at_condition = deviation <= band + COMPARISON_TOLERANCE
    return {
        "condition": condition,
        "cycle": cycle,
        "target_c": target,
        "measured_c": measured,
        "deviation_k": deviation,
        "at_condition": at_condition,
    }


def parameter_verdicts(check, parameter_limits):
    """Judge every parameter a check measured against its limits."""
    condition, cycle = check_key(check)
    if not isinstance(parameter_limits, dict) or not parameter_limits:
        raise ValueError("parameter_limits must be a non-empty mapping")
    measurements = check.get("measurements")
    if not isinstance(measurements, dict):
        raise ValueError(
            "check for %s of cycle %d carries no measurements mapping" % (condition, cycle)
        )
    verdicts = []
    for name in sorted(parameter_limits):
        bounds = parameter_limits[name]
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("limits for parameter '%s' must be a (lower, upper) pair" % name)
        lower = _as_float(bounds[0], "lower limit of '%s'" % name)
        upper = _as_float(bounds[1], "upper limit of '%s'" % name)
        if lower >= upper:
            raise ValueError("lower limit of '%s' must be below its upper limit" % name)
        if name not in measurements:
            verdicts.append(
                {"parameter": name, "measured": None, "within_limits": False, "missing": True}
            )
            continue
        measured = _as_float(measurements[name], "measurement of '%s'" % name)
        within = (
            measured > lower - COMPARISON_TOLERANCE
            and measured < upper + COMPARISON_TOLERANCE
        )
        verdicts.append(
            {
                "parameter": name,
                "measured": measured,
                "lower_limit": lower,
                "upper_limit": upper,
                "within_limits": within,
                "missing": False,
            }
        )
    return verdicts


def relative_drift(before, after):
    """Return the magnitude of the relative change between two readings."""
    first = _as_float(before, "before")
    second = _as_float(after, "after")
    if first == 0.0:
        raise ValueError("relative drift is undefined against a zero reference reading")
    return abs(second - first) / abs(first)


def ambient_drift(pre_check, post_check, parameter_limits, allowable_fraction):
    """Compare the two ambient references parameter by parameter."""
    allowed = _as_float(allowable_fraction, "allowable_fraction")
    if allowed < 0.0:
        raise ValueError("allowable_fraction must be non-negative, got %g" % allowed)
    if not isinstance(parameter_limits, dict) or not parameter_limits:
        raise ValueError("parameter_limits must be a non-empty mapping")
    pre = pre_check.get("measurements") if isinstance(pre_check, dict) else None
    post = post_check.get("measurements") if isinstance(post_check, dict) else None
    if not isinstance(pre, dict) or not isinstance(post, dict):
        raise ValueError("both ambient references must carry a measurements mapping")
    results = []
    for name in sorted(parameter_limits):
        if name not in pre or name not in post:
            results.append({"parameter": name, "drift": None, "acceptable": False})
            continue
        drift = relative_drift(pre[name], post[name])
        acceptable = drift < allowed + COMPARISON_TOLERANCE
        results.append({"parameter": name, "drift": drift, "acceptable": acceptable})
    return results


def assess_functional_verification(spec):
    """Judge the functional verification of an assembly across a thermal campaign.

    spec keys: cycle_count, checks, parameter_limits, target_temperatures,
    band_k, allowable_drift_fraction, optional intermediate_every.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("cycle_count", "checks", "parameter_limits", "target_temperatures",
                "band_k", "allowable_drift_fraction"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required = required_check_points(spec["cycle_count"], spec.get("intermediate_every"))
    performed = index_checks(spec["checks"])
    cover = coverage(required, performed)

    findings = []
    for condition, cycle in cover["missing"]:
        findings.append("no functional check at %s of cycle %d" % (condition, cycle))
    for condition, cycle in cover["unscheduled"]:
        findings.append(
            "functional check at %s of cycle %d matches no required point" % (condition, cycle)
        )

    condition_results = []
    parameter_results = {}
    for key in sorted(performed):
        check = performed[key]
        placement = check_at_condition(check, spec["target_temperatures"], spec["band_k"])
        condition_results.append(placement)
        if not placement["at_condition"]:
            findings.append(
                "check at %s of cycle %d was taken %.2f K off its condition"
                % (key[0], key[1], placement["deviation_k"])
            )
        verdicts = parameter_verdicts(check, spec["parameter_limits"])
        parameter_results[key] = verdicts
        for verdict in verdicts:
            if verdict["missing"]:
                findings.append(
                    "check at %s of cycle %d never measured '%s'"
                    % (key[0], key[1], verdict["parameter"])
                )
            elif not verdict["within_limits"]:
                findings.append(
                    "'%s' read %g at %s of cycle %d, outside its limits"
                    % (verdict["parameter"], verdict["measured"], key[0], key[1])
                )

    drift_results = None
    pre_key = ("ambient-pre", 0)
    post_key = ("ambient-post", spec["cycle_count"] + 1)
    if pre_key in performed and post_key in performed:
        drift_results = ambient_drift(
            performed[pre_key],
            performed[post_key],
            spec["parameter_limits"],
            spec["allowable_drift_fraction"],
        )
        for result in drift_results:
            if result["drift"] is None:
                findings.append(
                    "'%s' is not measured at both ambient references" % result["parameter"]
                )
            elif not result["acceptable"]:
                findings.append(
                    "'%s' drifted %.4f across the campaign, beyond the allowed %.4f"
                    % (result["parameter"], result["drift"],
                       float(spec["allowable_drift_fraction"]))
                )

    extremes_exercised = all(
        key in performed
        for key in [(c, cycle) for c in EXTREME_CONDITIONS for cycle in (1, spec["cycle_count"])]
    )
    return {
        "coverage": cover,
        "conditions": condition_results,
        "parameters": parameter_results,
        "drift": drift_results,
        "extremes_exercised": extremes_exercised,
        "verified": cover["complete"] and not findings,
        "findings": findings,
    }
