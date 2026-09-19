"""Readiness of a flammability test facility: chamber, gas supply, ignition source.

Anchor: ECSS-Q-ST-70-21C, quality assurance of the test installation (control of
the test facility, the purity of the supplied gases and the calibration of the
ignition source). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Compute the oxygen fraction actually delivered to the chamber from the
   supply purities and the set flows, rather than taking the flow-controller
   set point as the atmosphere. The oxygen carried as an impurity in the
   diluent counts, and at a tight tolerance it is the term that decides.
2. Compare the delivered fraction with the target through a named tolerance,
   counting a value exactly on the tolerance edge as inside it.
3. Grade every calibration against the planned test date, not against today,
   and warn on one that expires inside the campaign.
4. Check the ignition source against its flame-height and application-time
   windows and the chamber against its leak-rate limit, then separate the
   findings that stop the run from the ones worth recording.
"""

import datetime
import math

__all__ = [
    "CONCENTRATION_TOLERANCE_PCT",
    "DEFAULT_WARNING_DAYS",
    "IGNITION_WINDOWS",
    "parse_iso_date",
    "blended_oxygen_fraction",
    "oxygen_concentration_check",
    "calibration_status",
    "calibration_review",
    "ignition_source_check",
    "leak_rate_check",
    "assess_facility",
]

# Tolerance on the delivered oxygen concentration, in percentage points.
CONCENTRATION_TOLERANCE_PCT = 0.5

# A calibration expiring inside this window of the test date is reported so the
# campaign is not planned across its expiry.
DEFAULT_WARNING_DAYS = 30

# Windows the ignition source has to sit inside for a screening run to count.
IGNITION_WINDOWS = {
    "flame_height_mm": (18.0, 22.0),
    "application_time_s": (14.0, 16.0),
}

# A comparison against a window edge is a representation question, absorbed
# here instead of by moving the edge.
_EDGE_TOLERANCE = 1e-9


def _real(value, label, minimum=None, maximum=None):
    """Return value as a finite float inside its allowed span."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and number < minimum:
        raise ValueError("%s must be at least %g, got %g" % (label, minimum, number))
    if maximum is not None and number > maximum:
        raise ValueError("%s must be at most %g, got %g" % (label, maximum, number))
    return number


def _within(value, lower, upper):
    """True when value lies in the closed window, edges counted as inside."""
    below = value < lower and not math.isclose(value, lower, rel_tol=0.0,
                                               abs_tol=_EDGE_TOLERANCE)
    above = value > upper and not math.isclose(value, upper, rel_tol=0.0,
                                               abs_tol=_EDGE_TOLERANCE)
    return not below and not above


def parse_iso_date(value, label="date"):
    """Return an ISO-8601 calendar date, refusing anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO-8601 date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO-8601 calendar date: %r" % (label, value))


def blended_oxygen_fraction(oxygen_flow_lpm, oxygen_purity,
                            diluent_flow_lpm, diluent_oxygen_impurity=0.0):
    """Return the oxygen fraction actually delivered by the two supply lines."""
    o2_flow = _real(oxygen_flow_lpm, "oxygen_flow_lpm", minimum=0.0)
    n2_flow = _real(diluent_flow_lpm, "diluent_flow_lpm", minimum=0.0)
    purity = _real(oxygen_purity, "oxygen_purity", minimum=0.0, maximum=1.0)
    impurity = _real(diluent_oxygen_impurity, "diluent_oxygen_impurity",
                     minimum=0.0, maximum=1.0)
    total = o2_flow + n2_flow
    if total <= 0.0:
        raise ValueError("the supply lines deliver no flow at all")
    return (o2_flow * purity + n2_flow * impurity) / total


def oxygen_concentration_check(delivered_fraction, target_pct,
                               tolerance_pct=CONCENTRATION_TOLERANCE_PCT):
    """Compare the delivered oxygen concentration with its target."""
    delivered = _real(delivered_fraction, "delivered_fraction",
                      minimum=0.0, maximum=1.0)
    target = _real(target_pct, "target_pct", minimum=0.0, maximum=100.0)
    tolerance = _real(tolerance_pct, "tolerance_pct", minimum=0.0)
    delivered_pct = delivered * 100.0
    deviation = delivered_pct - target
    inside = _within(deviation, -tolerance, tolerance)
    return {
        "delivered_pct": delivered_pct,
        "target_pct": target,
        "deviation_pct": deviation,
        "tolerance_pct": tolerance,
        "inside_tolerance": inside,
    }


def calibration_status(due_date, test_date, warning_days=DEFAULT_WARNING_DAYS):
    """Grade one calibration against the planned test date."""
    if isinstance(warning_days, bool) or not isinstance(warning_days, int):
        raise ValueError("warning_days must be an integer")
    if warning_days < 0:
        raise ValueError("warning_days must not be negative")
    due = parse_iso_date(due_date, "due_date")
    planned = parse_iso_date(test_date, "test_date")
    if due < planned:
        return "expired"
    if (due - planned).days <= warning_days:
        return "due-soon"
    return "in-date"


def calibration_review(calibrations, test_date, warning_days=DEFAULT_WARNING_DAYS):
    """Grade every declared calibration and return the records in name order."""
    if not isinstance(calibrations, dict) or not calibrations:
        raise ValueError("calibrations must be a non-empty mapping of item to due date")
    records = []
    for name in sorted(calibrations):
        records.append({
            "item": name,
            "due_date": parse_iso_date(calibrations[name],
                                       "due date for %s" % name).isoformat(),
            "status": calibration_status(calibrations[name], test_date, warning_days),
        })
    return records


def ignition_source_check(flame_height_mm, application_time_s,
                          windows=IGNITION_WINDOWS):
    """Check the ignition source against its flame and timing windows."""
    if not isinstance(windows, dict):
        raise ValueError("windows must be a mapping of parameter to (lower, upper)")
    findings = []
    values = {"flame_height_mm": flame_height_mm,
              "application_time_s": application_time_s}
    graded = {}
    for key, raw in values.items():
        if key not in windows:
            raise ValueError("no window declared for %s" % key)
        window = windows[key]
        if not isinstance(window, (list, tuple)) or len(window) != 2:
            raise ValueError("window for %s must be a (lower, upper) pair" % key)
        lower = _real(window[0], "%s lower window" % key)
        upper = _real(window[1], "%s upper window" % key)
        if lower > upper:
            raise ValueError("window for %s is inverted" % key)
        value = _real(raw, key, minimum=0.0)
        inside = _within(value, lower, upper)
        graded[key] = {"value": value, "lower": lower, "upper": upper,
                       "inside": inside}
        if not inside:
            findings.append("%s of %g is outside its %g to %g window"
                            % (key.replace("_", " "), value, lower, upper))
    return {"parameters": graded, "findings": findings,
            "calibrated": not findings}


def leak_rate_check(measured_leak_rate, limit):
    """Check the chamber leak rate against its limit."""
    measured = _real(measured_leak_rate, "measured_leak_rate", minimum=0.0)
    bound = _real(limit, "leak-rate limit", minimum=0.0)
    inside = measured < bound or math.isclose(measured, bound, rel_tol=0.0,
                                              abs_tol=_EDGE_TOLERANCE)
    return {"measured": measured, "limit": bound, "inside_limit": inside,
            "margin": bound - measured}


def assess_facility(spec):
    """Run the full facility-readiness assessment for one planned test date.

    spec keys: test_date, oxygen_flow_lpm, oxygen_purity, diluent_flow_lpm,
    target_oxygen_pct, calibrations; optional diluent_oxygen_impurity,
    concentration_tolerance_pct, warning_days, flame_height_mm,
    application_time_s, leak_rate, leak_rate_limit.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = ("test_date", "oxygen_flow_lpm", "oxygen_purity",
                "diluent_flow_lpm", "target_oxygen_pct", "calibrations")
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    test_date = parse_iso_date(spec["test_date"], "test_date")
    delivered = blended_oxygen_fraction(
        spec["oxygen_flow_lpm"], spec["oxygen_purity"], spec["diluent_flow_lpm"],
        spec.get("diluent_oxygen_impurity", 0.0))
    oxygen = oxygen_concentration_check(
        delivered, spec["target_oxygen_pct"],
        spec.get("concentration_tolerance_pct", CONCENTRATION_TOLERANCE_PCT))
    calibrations = calibration_review(spec["calibrations"], test_date,
                                      spec.get("warning_days", DEFAULT_WARNING_DAYS))
    ignition = ignition_source_check(spec.get("flame_height_mm", 20.0),
                                     spec.get("application_time_s", 15.0))
    leak = leak_rate_check(spec.get("leak_rate", 0.0),
                           spec.get("leak_rate_limit", 1.0))
    blocking = []
    advisory = []
    if not oxygen["inside_tolerance"]:
        blocking.append("delivered oxygen concentration %.4f percent is %.4f "
                        "percentage points off the %.4f percent target"
                        % (oxygen["delivered_pct"], oxygen["deviation_pct"],
                           oxygen["target_pct"]))
    for record in calibrations:
        if record["status"] == "expired":
            blocking.append("the calibration of %s expired on %s, before the "
                            "planned test date" % (record["item"], record["due_date"]))
        elif record["status"] == "due-soon":
            advisory.append("the calibration of %s falls due on %s, inside the "
                            "campaign" % (record["item"], record["due_date"]))
    blocking.extend(ignition["findings"])
    if not leak["inside_limit"]:
        blocking.append("chamber leak rate %g is past its limit of %g"
                        % (leak["measured"], leak["limit"]))
    return {
        "test_date": test_date.isoformat(),
        "oxygen": oxygen,
        "calibrations": calibrations,
        "ignition": ignition,
        "leak": leak,
        "blocking": blocking,
        "advisory": advisory,
        "ready": not blocking,
    }
