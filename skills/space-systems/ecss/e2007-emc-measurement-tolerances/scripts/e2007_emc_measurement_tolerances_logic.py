#!/usr/bin/env python3
"""EMC measurement tolerance logic (ECSS-E-ST-20-07C, 5.2.1).

Offline, deterministic, standard-library only. The module fixes and checks
the deviations permitted while a compatibility measurement is performed:

* separation between the radiating item and the measuring antenna,
* frequency of the tuned point against the frequency it was meant to be,
* amplitude of the applied or indicated level against its target,
* frequency-band selection, scan-step coarseness and dwell duration,
* root-sum-square combination of the measurement-uncertainty terms,
* per-point and whole-sweep acceptance of the measurement run.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "REL_TOL",
    "DISTANCE_TOLERANCE_FRACTION",
    "DISTANCE_TOLERANCE_FLOOR_M",
    "FREQUENCY_TOLERANCE_FRACTION",
    "AMPLITUDE_TOLERANCE_DB",
    "MEASUREMENT_BANDS",
    "percent_deviation",
    "check_distance_tolerance",
    "check_frequency_tolerance",
    "check_amplitude_tolerance",
    "select_band",
    "check_scan_step",
    "check_dwell_time",
    "measurement_uncertainty_rss",
    "check_uncertainty_budget",
    "evaluate_measurement_point",
    "assess_measurement_campaign",
]

# Absorbs binary-representation error when a deviation computed as a
# difference or a ratio lands a few ULPs outside an exactly-met tolerance.
# It never widens the tolerance itself.
REL_TOL = 1e-9

# Separation between the item under measurement and the antenna may deviate
# by this fraction of the nominal separation, with an absolute floor so that
# a very short separation still carries a workable band.
DISTANCE_TOLERANCE_FRACTION = 0.05
DISTANCE_TOLERANCE_FLOOR_M = 0.01

# The tuned frequency may deviate by this fraction of the intended frequency.
FREQUENCY_TOLERANCE_FRACTION = 0.02

# The applied or indicated level may deviate from its target by this many dB.
AMPLITUDE_TOLERANCE_DB = 2.0

# (lower_hz, upper_hz, resolution_bandwidth_hz, max_step_fraction, min_dwell_s)
# The band sets the resolution bandwidth, how coarsely the sweep may step
# between adjacent points, and how long each point is observed.
MEASUREMENT_BANDS = (
    (30.0, 1.0e3, 10.0, 0.010, 1.0),
    (1.0e3, 1.0e4, 100.0, 0.010, 1.0),
    (1.0e4, 1.5e5, 1.0e3, 0.010, 1.0),
    (1.5e5, 3.0e7, 1.0e4, 0.005, 0.5),
    (3.0e7, 1.0e9, 1.0e5, 0.005, 0.2),
    (1.0e9, 1.8e10, 1.0e6, 0.005, 0.1),
)

SWEEP_LOWER_HZ = MEASUREMENT_BANDS[0][0]
SWEEP_UPPER_HZ = MEASUREMENT_BANDS[-1][1]

_POINT_KEYS = (
    "id",
    "nominal_frequency_hz",
    "actual_frequency_hz",
    "nominal_distance_m",
    "actual_distance_m",
    "target_amplitude_db",
    "actual_amplitude_db",
    "dwell_s",
)


def _finding(code, subject, detail):
    """Build one measurement finding record."""
    return {"code": code, "subject": subject, "detail": detail}


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %s" % (label, type(value).__name__))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _within(deviation, allowed):
    """Tolerance comparison that absorbs binary-representation error."""
    return deviation <= allowed or math.isclose(
        deviation, allowed, rel_tol=REL_TOL, abs_tol=0.0
    )


def percent_deviation(nominal, actual):
    """Signed deviation of actual from nominal, in percent of nominal."""
    base = _as_positive_float(nominal, "nominal value")
    value = _as_float(actual, "actual value")
    return (value - base) / base * 100.0


def check_distance_tolerance(nominal_m, actual_m):
    """Check the antenna separation against the permitted deviation."""
    nominal = _as_positive_float(nominal_m, "nominal_distance_m")
    actual = _as_positive_float(actual_m, "actual_distance_m")
    allowed = max(nominal * DISTANCE_TOLERANCE_FRACTION, DISTANCE_TOLERANCE_FLOOR_M)
    deviation = abs(actual - nominal)
    return {
        "quantity": "separation",
        "nominal": nominal,
        "actual": actual,
        "deviation": deviation,
        "allowed": allowed,
        "percent": percent_deviation(nominal, actual),
        "within": _within(deviation, allowed),
    }


def check_frequency_tolerance(nominal_hz, actual_hz):
    """Check the tuned frequency against the permitted deviation."""
    nominal = _as_positive_float(nominal_hz, "nominal_frequency_hz")
    actual = _as_positive_float(actual_hz, "actual_frequency_hz")
    allowed = nominal * FREQUENCY_TOLERANCE_FRACTION
    deviation = abs(actual - nominal)
    return {
        "quantity": "frequency",
        "nominal": nominal,
        "actual": actual,
        "deviation": deviation,
        "allowed": allowed,
        "percent": percent_deviation(nominal, actual),
        "within": _within(deviation, allowed),
    }


def check_amplitude_tolerance(target_db, actual_db, allowed_db=AMPLITUDE_TOLERANCE_DB):
    """Check the applied or indicated level against the permitted deviation."""
    target = _as_float(target_db, "target_amplitude_db")
    actual = _as_float(actual_db, "actual_amplitude_db")
    allowed = _as_positive_float(allowed_db, "allowed_db")
    deviation = abs(actual - target)
    return {
        "quantity": "amplitude",
        "nominal": target,
        "actual": actual,
        "deviation": deviation,
        "allowed": allowed,
        "percent": None,
        "within": _within(deviation, allowed),
    }


def select_band(frequency_hz):
    """Return the measurement band that owns this frequency."""
    frequency = _as_positive_float(frequency_hz, "frequency_hz")
    if frequency < SWEEP_LOWER_HZ or frequency > SWEEP_UPPER_HZ:
        raise ValueError(
            "frequency %r lies outside the measured range %r to %r Hz"
            % (frequency, SWEEP_LOWER_HZ, SWEEP_UPPER_HZ)
        )
    for lower, upper, bandwidth, step_fraction, dwell in MEASUREMENT_BANDS:
        if lower <= frequency <= upper:
            return {
                "lower_hz": lower,
                "upper_hz": upper,
                "resolution_bandwidth_hz": bandwidth,
                "max_step_fraction": step_fraction,
                "min_dwell_s": dwell,
            }
    raise ValueError("no measurement band covers frequency %r Hz" % (frequency,))


def check_scan_step(previous_hz, next_hz):
    """Check the step between two adjacent sweep points."""
    previous = _as_positive_float(previous_hz, "previous_hz")
    following = _as_positive_float(next_hz, "next_hz")
    if following <= previous:
        raise ValueError(
            "a sweep step must increase in frequency: %r does not follow %r"
            % (next_hz, previous_hz)
        )
    band = select_band(previous)
    allowed = previous * band["max_step_fraction"]
    step = following - previous
    return {
        "quantity": "scan-step",
        "previous_hz": previous,
        "next_hz": following,
        "step_hz": step,
        "allowed_hz": allowed,
        "band": band,
        "within": _within(step, allowed),
    }


def check_dwell_time(frequency_hz, dwell_s):
    """Check that a sweep point is observed for long enough."""
    dwell = _as_positive_float(dwell_s, "dwell_s")
    band = select_band(frequency_hz)
    required = band["min_dwell_s"]
    return {
        "quantity": "dwell",
        "frequency_hz": _as_positive_float(frequency_hz, "frequency_hz"),
        "dwell_s": dwell,
        "required_s": required,
        "within": dwell >= required
        or math.isclose(dwell, required, rel_tol=REL_TOL, abs_tol=0.0),
    }


def measurement_uncertainty_rss(terms):
    """Combine independent uncertainty terms as a root-sum-square, in dB."""
    if isinstance(terms, (str, bytes)) or not hasattr(terms, "__iter__"):
        raise ValueError("uncertainty terms must be an iterable of dB values")
    total = 0.0
    count = 0
    for index, term in enumerate(terms):
        value = _as_float(term, "uncertainty term[%d]" % index)
        if value < 0.0:
            raise ValueError(
                "uncertainty term[%d] must not be negative, got %r" % (index, term)
            )
        total += value * value
        count += 1
    if count == 0:
        raise ValueError("at least one uncertainty term is required")
    return math.sqrt(total)


def check_uncertainty_budget(terms, allowed_db):
    """Compare the combined measurement uncertainty against its budget."""
    allowed = _as_positive_float(allowed_db, "allowed_db")
    combined = measurement_uncertainty_rss(terms)
    return {
        "quantity": "uncertainty",
        "combined_db": combined,
        "allowed_db": allowed,
        "margin_db": allowed - combined,
        "within": _within(combined, allowed),
    }


def evaluate_measurement_point(point):
    """Evaluate one measurement point against every applicable tolerance."""
    if not isinstance(point, dict):
        raise ValueError("point must be a mapping, got %s" % type(point).__name__)
    unknown = [key for key in point if key not in _POINT_KEYS]
    if unknown:
        raise ValueError(
            "point carries unknown key(s): %s" % ", ".join(sorted(unknown))
        )
    if "id" not in point:
        raise ValueError("point is missing required key 'id'")
    if not isinstance(point["id"], str) or not point["id"].strip():
        raise ValueError("point id must be a non-blank string")
    identifier = point["id"].strip()
    checks = {}
    findings = []
    has_frequency = (
        "nominal_frequency_hz" in point and "actual_frequency_hz" in point
    )
    if "nominal_frequency_hz" in point and "actual_frequency_hz" not in point:
        raise ValueError(
            "point %s declares a nominal frequency but no measured frequency"
            % identifier
        )
    if has_frequency:
        checks["frequency"] = check_frequency_tolerance(
            point["nominal_frequency_hz"], point["actual_frequency_hz"]
        )
        if not checks["frequency"]["within"]:
            findings.append(
                _finding(
                    "frequency-out-of-tolerance",
                    identifier,
                    "tuned %.6g Hz against an intended %.6g Hz (%.3f %% deviation)"
                    % (
                        checks["frequency"]["actual"],
                        checks["frequency"]["nominal"],
                        checks["frequency"]["percent"],
                    ),
                )
            )
    has_distance = "nominal_distance_m" in point and "actual_distance_m" in point
    if "nominal_distance_m" in point and "actual_distance_m" not in point:
        raise ValueError(
            "point %s declares a nominal separation but no measured separation"
            % identifier
        )
    if has_distance:
        checks["distance"] = check_distance_tolerance(
            point["nominal_distance_m"], point["actual_distance_m"]
        )
        if not checks["distance"]["within"]:
            findings.append(
                _finding(
                    "separation-out-of-tolerance",
                    identifier,
                    "set at %.4f m against a nominal %.4f m (allowed %.4f m)"
                    % (
                        checks["distance"]["actual"],
                        checks["distance"]["nominal"],
                        checks["distance"]["allowed"],
                    ),
                )
            )
    has_amplitude = (
        "target_amplitude_db" in point and "actual_amplitude_db" in point
    )
    if "target_amplitude_db" in point and "actual_amplitude_db" not in point:
        raise ValueError(
            "point %s declares a target amplitude but no measured amplitude"
            % identifier
        )
    if has_amplitude:
        checks["amplitude"] = check_amplitude_tolerance(
            point["target_amplitude_db"], point["actual_amplitude_db"]
        )
        if not checks["amplitude"]["within"]:
            findings.append(
                _finding(
                    "amplitude-out-of-tolerance",
                    identifier,
                    "held at %.3f dB against a target %.3f dB (allowed %.3f dB)"
                    % (
                        checks["amplitude"]["actual"],
                        checks["amplitude"]["nominal"],
                        checks["amplitude"]["allowed"],
                    ),
                )
            )
    if not checks:
        raise ValueError(
            "point %s carries no toleranced quantity (frequency, separation or "
            "amplitude)" % identifier
        )
    if "dwell_s" in point:
        if not has_frequency:
            raise ValueError(
                "point %s declares a dwell but no frequency to band it" % identifier
            )
        checks["dwell"] = check_dwell_time(
            point["nominal_frequency_hz"], point["dwell_s"]
        )
        if not checks["dwell"]["within"]:
            findings.append(
                _finding(
                    "dwell-too-short",
                    identifier,
                    "observed %.4f s against the %.4f s its band requires"
                    % (checks["dwell"]["dwell_s"], checks["dwell"]["required_s"]),
                )
            )
    return {
        "id": identifier,
        "checks": checks,
        "findings": findings,
        "within_tolerance": not findings,
    }


def assess_measurement_campaign(points, uncertainty_terms=None, uncertainty_budget_db=None):
    """Assess a swept measurement run point by point and as a whole."""
    if isinstance(points, (str, bytes)) or not hasattr(points, "__iter__"):
        raise ValueError("points must be an iterable of measurement points")
    evaluated = [evaluate_measurement_point(point) for point in points]
    if not evaluated:
        raise ValueError("a measurement run must contain at least one point")
    seen = set()
    for record in evaluated:
        if record["id"] in seen:
            raise ValueError("measurement point %r appears twice" % record["id"])
        seen.add(record["id"])
    findings = []
    for record in evaluated:
        findings.extend(record["findings"])
    steps = []
    previous = None
    for record in evaluated:
        frequency_check = record["checks"].get("frequency")
        if frequency_check is None:
            previous = None
            continue
        current = frequency_check["nominal"]
        if previous is not None:
            if current <= previous:
                findings.append(
                    _finding(
                        "sweep-not-ascending",
                        record["id"],
                        "point at %.6g Hz does not follow the previous %.6g Hz"
                        % (current, previous),
                    )
                )
            else:
                step = check_scan_step(previous, current)
                steps.append(step)
                if not step["within"]:
                    findings.append(
                        _finding(
                            "scan-step-too-coarse",
                            record["id"],
                            "stepped %.6g Hz from %.6g Hz, above the %.6g Hz its "
                            "band allows"
                            % (step["step_hz"], previous, step["allowed_hz"]),
                        )
                    )
        previous = current
    uncertainty = None
    if uncertainty_terms is not None or uncertainty_budget_db is not None:
        if uncertainty_terms is None or uncertainty_budget_db is None:
            raise ValueError(
                "an uncertainty budget needs both the terms and the allowance"
            )
        uncertainty = check_uncertainty_budget(uncertainty_terms, uncertainty_budget_db)
        if not uncertainty["within"]:
            findings.append(
                _finding(
                    "uncertainty-over-budget",
                    "measurement-run",
                    "combined uncertainty %.4f dB against a %.4f dB allowance"
                    % (uncertainty["combined_db"], uncertainty["allowed_db"]),
                )
            )
    accepted = not findings
    return {
        "verdict": "within-tolerance" if accepted else "out-of-tolerance",
        "accepted": accepted,
        "findings": findings,
        "points": evaluated,
        "point_count": len(evaluated),
        "step_count": len(steps),
        "uncertainty": uncertainty,
        "conforming_fraction": sum(
            1 for record in evaluated if record["within_tolerance"]
        )
        / float(len(evaluated)),
    }
