"""Control of particle counters and sizing microscopes used for cleanliness monitoring.

Anchor: ECSS-Q-ST-70-50C, the clause on control of the monitoring instruments.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
An instrument is fit to produce monitoring data only when four independent
properties hold at the same time:

1. calibration currency -- how far into its interval the instrument is, and
   whether it is inside, close to the end of, or past it;
2. sample flow accuracy -- the deviation of the measured flow from nominal,
   and the bias that deviation injects into every reported concentration,
   because the instrument divides its counts by the nominal volume, not the
   volume it actually drew;
3. threshold sensitivity -- the counting efficiency at the smallest reported
   channel, against the acceptance window around its target;
4. background -- the count rate of a filtered zero run, against the rate the
   programme allows.

A sizing microscope is graded on the same pattern with a stage-micrometer
bias in place of flow. Every check is graded independently and the overall
fitness is their conjunction: a single failed check withholds fitness, and
the passing checks do not average it back.
"""

import math

__all__ = [
    "COMPARE_TOLERANCE",
    "CALIBRATION_STATES",
    "require_real",
    "require_int",
    "calibration_status",
    "flow_deviation_fraction",
    "concentration_bias_fraction",
    "grade_flow",
    "grade_counting_efficiency",
    "zero_count_rate_per_m3",
    "grade_background",
    "grade_microscope_sizing",
    "assess_instrument_control",
]

# Every grading here is a magnitude against a window edge; an exact equality
# can land a few ULPs outside. Absorb the representation error, never by
# widening the acceptance window itself.
COMPARE_TOLERANCE = 1e-9

CALIBRATION_STATES = ("current", "due-soon", "expired")

LITRES_PER_CUBIC_METRE = 1000.0


def require_real(value, label, positive=False, non_negative=False):
    """Return value as a float, rejecting booleans, strings and non-finites."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and result <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, result))
    if non_negative and result < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, result))
    return result


def require_int(value, label, non_negative=False, positive=False):
    """Return value as an int, rejecting booleans and floats."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if positive and value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    if non_negative and value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _within(value, limit):
    """True when value does not exceed limit, absorbing representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=COMPARE_TOLERANCE, abs_tol=COMPARE_TOLERANCE
    )


def calibration_status(days_since_calibration, interval_days, warning_days=30):
    """Grade how far into its calibration interval an instrument has run."""
    elapsed = require_int(days_since_calibration, "days_since_calibration",
                          non_negative=True)
    interval = require_int(interval_days, "interval_days", positive=True)
    warning = require_int(warning_days, "warning_days", non_negative=True)
    if warning >= interval:
        raise ValueError(
            "warning_days %d must be shorter than the interval %d" % (warning, interval)
        )
    remaining = interval - elapsed
    if remaining < 0:
        state = "expired"
    elif remaining <= warning:
        state = "due-soon"
    else:
        state = "current"
    return {
        "state": state,
        "days_remaining": remaining,
        "interval_days": interval,
        "conforming": state != "expired",
    }


def flow_deviation_fraction(measured_lpm, nominal_lpm):
    """Return the signed deviation of the measured flow from nominal."""
    measured = require_real(measured_lpm, "measured_lpm", positive=True)
    nominal = require_real(nominal_lpm, "nominal_lpm", positive=True)
    return (measured - nominal) / nominal


def concentration_bias_fraction(measured_lpm, nominal_lpm):
    """Return the bias a flow deviation injects into a reported concentration.

    The counter divides its counts by the nominal sampled volume. Drawing less
    than nominal therefore over-reports concentration and drawing more
    under-reports it.
    """
    measured = require_real(measured_lpm, "measured_lpm", positive=True)
    nominal = require_real(nominal_lpm, "nominal_lpm", positive=True)
    return nominal / measured - 1.0


def grade_flow(measured_lpm, nominal_lpm, tolerance_fraction=0.05):
    """Grade the sample flow against its tolerance and report the induced bias."""
    tolerance = require_real(tolerance_fraction, "tolerance_fraction", positive=True)
    if tolerance >= 1.0:
        raise ValueError("tolerance_fraction must be below 1, got %g" % tolerance)
    deviation = flow_deviation_fraction(measured_lpm, nominal_lpm)
    bias = concentration_bias_fraction(measured_lpm, nominal_lpm)
    return {
        "deviation_fraction": deviation,
        "concentration_bias_fraction": bias,
        "tolerance_fraction": tolerance,
        "conforming": _within(abs(deviation), tolerance),
    }


def grade_counting_efficiency(efficiency, target=0.5, window=0.2):
    """Grade the counting efficiency at the smallest reported channel."""
    value = require_real(efficiency, "efficiency", non_negative=True)
    if value > 1.0:
        raise ValueError("efficiency must not exceed 1, got %g" % value)
    centre = require_real(target, "target", positive=True)
    if centre > 1.0:
        raise ValueError("target must not exceed 1, got %g" % centre)
    half = require_real(window, "window", positive=True)
    deviation = value - centre
    return {
        "efficiency": value,
        "target": centre,
        "window": half,
        "deviation": deviation,
        "conforming": _within(abs(deviation), half),
    }


def zero_count_rate_per_m3(counts, sampled_volume_litres):
    """Return the background count rate of a filtered zero run, per cubic metre."""
    total = require_int(counts, "counts", non_negative=True)
    volume = require_real(sampled_volume_litres, "sampled_volume_litres", positive=True)
    return total * LITRES_PER_CUBIC_METRE / volume


def grade_background(counts, sampled_volume_litres, allowed_per_m3):
    """Grade a filtered zero run against the allowed background rate."""
    allowed = require_real(allowed_per_m3, "allowed_per_m3", non_negative=True)
    rate = zero_count_rate_per_m3(counts, sampled_volume_litres)
    return {
        "counts": counts,
        "rate_per_m3": rate,
        "allowed_per_m3": allowed,
        "conforming": _within(rate, allowed),
    }


def grade_microscope_sizing(measured_um, certified_um, tolerance_um):
    """Grade a sizing microscope against a certified stage micrometer."""
    measured = require_real(measured_um, "measured_um", positive=True)
    certified = require_real(certified_um, "certified_um", positive=True)
    tolerance = require_real(tolerance_um, "tolerance_um", positive=True)
    bias = measured - certified
    return {
        "measured_um": measured,
        "certified_um": certified,
        "bias_um": bias,
        "bias_fraction": bias / certified,
        "tolerance_um": tolerance,
        "conforming": _within(abs(bias), tolerance),
    }


def assess_instrument_control(spec):
    """Grade a monitoring instrument for fitness to produce data.

    spec keys: instrument_id, kind ('particle-counter' or 'sizing-microscope'),
    calibration (days_since, interval_days, optional warning_days); for a
    counter also flow (measured_lpm, nominal_lpm, optional tolerance_fraction),
    efficiency (value, optional target and window) and background (counts,
    volume_litres, allowed_per_m3); for a microscope also sizing (measured_um,
    certified_um, tolerance_um).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    kind = spec.get("kind", "particle-counter")
    if kind not in ("particle-counter", "sizing-microscope"):
        raise ValueError(
            "kind must be 'particle-counter' or 'sizing-microscope', got %r" % (kind,)
        )
    if "calibration" not in spec:
        raise ValueError("spec missing required key 'calibration'")
    calibration_spec = spec["calibration"]
    if not isinstance(calibration_spec, dict):
        raise ValueError("spec['calibration'] must be a mapping")
    for key in ("days_since", "interval_days"):
        if key not in calibration_spec:
            raise ValueError("calibration missing required key '%s'" % key)
    checks = {}
    checks["calibration"] = calibration_status(
        calibration_spec["days_since"],
        calibration_spec["interval_days"],
        calibration_spec.get("warning_days", 30),
    )
    findings = []
    if not checks["calibration"]["conforming"]:
        findings.append(
            "calibration expired %d days ago; data taken after expiry is not "
            "traceable" % (-checks["calibration"]["days_remaining"])
        )
    elif checks["calibration"]["state"] == "due-soon":
        findings.append(
            "calibration falls due in %d days; schedule recall before the next "
            "monitoring campaign" % checks["calibration"]["days_remaining"]
        )
    if kind == "particle-counter":
        for key in ("flow", "efficiency", "background"):
            if key not in spec:
                raise ValueError("a particle counter needs the '%s' check" % key)
        flow_spec = spec["flow"]
        if not isinstance(flow_spec, dict):
            raise ValueError("spec['flow'] must be a mapping")
        for key in ("measured_lpm", "nominal_lpm"):
            if key not in flow_spec:
                raise ValueError("flow missing required key '%s'" % key)
        checks["flow"] = grade_flow(
            flow_spec["measured_lpm"],
            flow_spec["nominal_lpm"],
            flow_spec.get("tolerance_fraction", 0.05),
        )
        if not checks["flow"]["conforming"]:
            findings.append(
                "sample flow deviates by %.2f%%, biasing every reported "
                "concentration by %.2f%%"
                % (100.0 * checks["flow"]["deviation_fraction"],
                   100.0 * checks["flow"]["concentration_bias_fraction"])
            )
        efficiency_spec = spec["efficiency"]
        if not isinstance(efficiency_spec, dict) or "value" not in efficiency_spec:
            raise ValueError("spec['efficiency'] must be a mapping carrying 'value'")
        checks["efficiency"] = grade_counting_efficiency(
            efficiency_spec["value"],
            efficiency_spec.get("target", 0.5),
            efficiency_spec.get("window", 0.2),
        )
        if not checks["efficiency"]["conforming"]:
            findings.append(
                "counting efficiency %.3f at the smallest channel is outside the "
                "window %.3f around %.3f"
                % (checks["efficiency"]["efficiency"], checks["efficiency"]["window"],
                   checks["efficiency"]["target"])
            )
        background_spec = spec["background"]
        if not isinstance(background_spec, dict):
            raise ValueError("spec['background'] must be a mapping")
        for key in ("counts", "volume_litres", "allowed_per_m3"):
            if key not in background_spec:
                raise ValueError("background missing required key '%s'" % key)
        checks["background"] = grade_background(
            background_spec["counts"],
            background_spec["volume_litres"],
            background_spec["allowed_per_m3"],
        )
        if not checks["background"]["conforming"]:
            findings.append(
                "zero-run background %.4g per m3 exceeds the allowed %.4g per m3"
                % (checks["background"]["rate_per_m3"],
                   checks["background"]["allowed_per_m3"])
            )
    else:
        if "sizing" not in spec:
            raise ValueError("a sizing microscope needs the 'sizing' check")
        sizing_spec = spec["sizing"]
        if not isinstance(sizing_spec, dict):
            raise ValueError("spec['sizing'] must be a mapping")
        for key in ("measured_um", "certified_um", "tolerance_um"):
            if key not in sizing_spec:
                raise ValueError("sizing missing required key '%s'" % key)
        checks["sizing"] = grade_microscope_sizing(
            sizing_spec["measured_um"],
            sizing_spec["certified_um"],
            sizing_spec["tolerance_um"],
        )
        if not checks["sizing"]["conforming"]:
            findings.append(
                "stage-micrometer bias %.4g um exceeds the tolerance %.4g um"
                % (checks["sizing"]["bias_um"], checks["sizing"]["tolerance_um"])
            )
    blocking = [name for name, check in checks.items() if not check["conforming"]]
    return {
        "instrument_id": spec.get("instrument_id", "instrument"),
        "kind": kind,
        "checks": checks,
        "failed_checks": blocking,
        "fit_for_use": not blocking,
        "findings": findings,
    }
