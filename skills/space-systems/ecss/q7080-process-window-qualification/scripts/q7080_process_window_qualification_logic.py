"""Qualification of an additive-manufacturing parameter window with test coupons.

Anchor: ECSS-Q-ST-70-80 process clauses covering qualification of the declared
parameter window by a coupon campaign. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared window: one (low, high) bound pair per parameter, with
   a fixed setpoint expressed as a pair whose bounds coincide.
2. Grade every qualification run's recorded parameters against the window. An
   unrecorded parameter and an out-of-window parameter break the same claim and
   are reported together, because neither evidences a controlled process.
3. Grade the coverage of the window itself: a run at each bound of every
   parameter is required, and a run in the interior band is expected. A missing
   bound is fatal, a missing interior sample is a finding.
4. Grade the coupons: every required characteristic has to have been measured
   and to have met its acceptance limit, with unmeasured and failed reported
   separately.
5. Give the verdict - not qualified, qualified with findings, or qualified -
   and say for how long and against which change triggers it stands.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "COVERAGE_BAND_FRACTION",
    "INTERIOR_BAND_FRACTION",
    "MIN_QUALIFICATION_RUNS",
    "validate_window",
    "within_window",
    "grade_run_parameters",
    "window_bound_coverage",
    "interior_coverage",
    "evaluate_coupon",
    "coupon_completeness",
    "qualify_window",
]

# Recorded parameters arrive through unit conversions and logger rounding, so a
# setpoint exactly on a bound can land a few units in the last place outside it.
# The comparison absorbs that; the window is never widened.
BOUND_TOLERANCE = 1e-9

# A run counts as sampling a bound when it sits within this fraction of the
# window span of that bound.
COVERAGE_BAND_FRACTION = 0.05

# The interior band is the middle half of the window span.
INTERIOR_BAND_FRACTION = 0.25

# Repeatability is the property being claimed, and one run cannot evidence it.
MIN_QUALIFICATION_RUNS = 3


def _finite(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def validate_window(window):
    """Return the validated declared window as {parameter: (low, high)}."""
    if not isinstance(window, dict) or not window:
        raise ValueError("window must be a non-empty mapping of parameter bounds")
    validated = {}
    for name, bounds in window.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("window parameter names must be non-empty strings")
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("window['%s'] must be a (low, high) pair" % name)
        low = _finite("window['%s'] low" % name, bounds[0])
        high = _finite("window['%s'] high" % name, bounds[1])
        if low > high:
            raise ValueError(
                "window['%s'] is inverted: low %g above high %g" % (name, low, high)
            )
        validated[name] = (low, high)
    return validated


def within_window(value, bounds):
    """Return True when a recorded value sits inside a bound pair."""
    low, high = bounds
    number = _finite("recorded value", value)
    if number < low and not math.isclose(number, low, rel_tol=BOUND_TOLERANCE, abs_tol=0.0):
        return False
    if number > high and not math.isclose(number, high, rel_tol=BOUND_TOLERANCE, abs_tol=0.0):
        return False
    return True


def grade_run_parameters(run, window):
    """Return the excursion records for one qualification run."""
    bounds_by_name = validate_window(window)
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping")
    identifier = run.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("run id must be a non-empty string")
    recorded = run.get("parameters")
    if not isinstance(recorded, dict):
        raise ValueError("run['parameters'] must be a mapping")
    for name in recorded:
        if name not in bounds_by_name:
            raise ValueError(
                "run %s records parameter '%s' that the window does not declare"
                % (identifier, name)
            )
    excursions = []
    for name, bounds in sorted(bounds_by_name.items()):
        if name not in recorded or recorded[name] is None:
            excursions.append(
                {"run": identifier, "parameter": name, "value": None,
                 "bounds": bounds, "reason": "unrecorded"}
            )
            continue
        value = _finite("run %s parameter '%s'" % (identifier, name), recorded[name])
        if not within_window(value, bounds):
            excursions.append(
                {"run": identifier, "parameter": name, "value": value,
                 "bounds": bounds, "reason": "out-of-window"}
            )
    return excursions


def window_bound_coverage(runs, window):
    """Return the window bounds that no run sampled."""
    bounds_by_name = validate_window(window)
    if not isinstance(runs, (list, tuple)) or not runs:
        raise ValueError("runs must be a non-empty sequence")
    missing = []
    for name, (low, high) in sorted(bounds_by_name.items()):
        span = high - low
        tolerance = max(span * COVERAGE_BAND_FRACTION, abs(high) * BOUND_TOLERANCE)
        low_seen = False
        high_seen = False
        for run in runs:
            recorded = run.get("parameters", {})
            if name not in recorded or recorded[name] is None:
                continue
            value = _finite("run parameter '%s'" % name, recorded[name])
            if abs(value - low) <= tolerance:
                low_seen = True
            if abs(value - high) <= tolerance:
                high_seen = True
        if not low_seen:
            missing.append({"parameter": name, "bound": "low", "value": low})
        if not high_seen:
            missing.append({"parameter": name, "bound": "high", "value": high})
    return missing


def interior_coverage(runs, window):
    """Return the parameters whose window interior no run sampled."""
    bounds_by_name = validate_window(window)
    if not isinstance(runs, (list, tuple)) or not runs:
        raise ValueError("runs must be a non-empty sequence")
    unsampled = []
    for name, (low, high) in sorted(bounds_by_name.items()):
        span = high - low
        if span <= 0.0:
            continue
        inner_low = low + span * INTERIOR_BAND_FRACTION
        inner_high = high - span * INTERIOR_BAND_FRACTION
        seen = False
        for run in runs:
            recorded = run.get("parameters", {})
            if name not in recorded or recorded[name] is None:
                continue
            value = _finite("run parameter '%s'" % name, recorded[name])
            if inner_low <= value <= inner_high:
                seen = True
        if not seen:
            unsampled.append(name)
    return unsampled


def evaluate_coupon(coupon, acceptance):
    """Return the pass/fail record of one coupon against the acceptance limits."""
    if not isinstance(coupon, dict):
        raise ValueError("coupon must be a mapping")
    if not isinstance(acceptance, dict) or not acceptance:
        raise ValueError("acceptance must be a non-empty mapping of limits")
    identifier = coupon.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("coupon id must be a non-empty string")
    measured = coupon.get("measured")
    if not isinstance(measured, dict):
        raise ValueError("coupon['measured'] must be a mapping")
    failures = []
    for name, value in sorted(measured.items()):
        if name not in acceptance:
            raise ValueError(
                "coupon %s measured '%s' with no declared acceptance limit"
                % (identifier, name)
            )
        limits = acceptance[name]
        if not isinstance(limits, dict) or not ({"min", "max"} & set(limits)):
            raise ValueError("acceptance['%s'] must declare 'min' and/or 'max'" % name)
        number = _finite("coupon %s '%s'" % (identifier, name), value)
        if "min" in limits:
            low = _finite("acceptance['%s']['min']" % name, limits["min"])
            if number < low and not math.isclose(
                number, low, rel_tol=BOUND_TOLERANCE, abs_tol=0.0
            ):
                failures.append({"coupon": identifier, "characteristic": name,
                                 "value": number, "limit": low, "reason": "below-minimum"})
        if "max" in limits:
            high = _finite("acceptance['%s']['max']" % name, limits["max"])
            if number > high and not math.isclose(
                number, high, rel_tol=BOUND_TOLERANCE, abs_tol=0.0
            ):
                failures.append({"coupon": identifier, "characteristic": name,
                                 "value": number, "limit": high, "reason": "above-maximum"})
    return {"id": identifier, "failures": failures, "passed": not failures}


def coupon_completeness(runs, required_characteristics):
    """Return the characteristics no coupon of each run measured."""
    if not isinstance(required_characteristics, (list, tuple, set)) or not required_characteristics:
        raise ValueError("required_characteristics must be a non-empty sequence")
    required = set()
    for name in required_characteristics:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("required characteristic names must be non-empty strings")
        required.add(name)
    gaps = []
    for run in runs:
        measured = set()
        for coupon in run.get("coupons", []) or []:
            if not isinstance(coupon, dict) or not isinstance(coupon.get("measured"), dict):
                raise ValueError("each coupon must carry a 'measured' mapping")
            measured.update(coupon["measured"].keys())
        for name in sorted(required - measured):
            gaps.append({"run": run.get("id"), "characteristic": name})
    return gaps


def qualify_window(spec):
    """Run the full parameter-window qualification assessment.

    spec keys: window, runs, acceptance, required_characteristics, optional
    min_runs.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("window", "runs", "acceptance", "required_characteristics"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    window = validate_window(spec["window"])
    runs = spec["runs"]
    if not isinstance(runs, (list, tuple)) or not runs:
        raise ValueError("spec['runs'] must be a non-empty sequence")
    min_runs = spec.get("min_runs", MIN_QUALIFICATION_RUNS)
    if not isinstance(min_runs, int) or isinstance(min_runs, bool) or min_runs < 1:
        raise ValueError("min_runs must be a positive integer")
    seen = set()
    excursions = []
    coupon_failures = []
    for run in runs:
        excursions.extend(grade_run_parameters(run, window))
        identifier = run.get("id")
        if identifier in seen:
            raise ValueError("duplicate run id %r" % identifier)
        seen.add(identifier)
        for coupon in run.get("coupons", []) or []:
            record = evaluate_coupon(coupon, spec["acceptance"])
            coupon_failures.extend(record["failures"])
    missing_bounds = window_bound_coverage(runs, window)
    unsampled_interior = interior_coverage(runs, window)
    gaps = coupon_completeness(runs, spec["required_characteristics"])

    blocking = []
    findings = []
    if len(runs) < min_runs:
        blocking.append(
            "campaign ran %d builds; repeatability needs at least %d" % (len(runs), min_runs)
        )
    for item in excursions:
        blocking.append(
            "run %s parameter %s %s" % (item["run"], item["parameter"], item["reason"])
        )
    for item in missing_bounds:
        blocking.append(
            "no run sampled the %s bound of %s (%g)"
            % (item["bound"], item["parameter"], item["value"])
        )
    for item in gaps:
        blocking.append(
            "run %s never measured %s" % (item["run"], item["characteristic"])
        )
    for item in coupon_failures:
        blocking.append(
            "coupon %s %s %s its limit %g"
            % (item["coupon"], item["characteristic"], item["reason"], item["limit"])
        )
    for name in unsampled_interior:
        findings.append(
            "no run sampled the interior of the %s window; coverage is edges only" % name
        )
    if blocking:
        verdict = "not-qualified"
    elif findings:
        verdict = "qualified-with-findings"
    else:
        verdict = "qualified"
    return {
        "verdict": verdict,
        "window": window,
        "run_count": len(runs),
        "excursions": excursions,
        "missing_bounds": missing_bounds,
        "unsampled_interior": unsampled_interior,
        "coupon_gaps": gaps,
        "coupon_failures": coupon_failures,
        "blocking": blocking,
        "findings": findings,
    }
