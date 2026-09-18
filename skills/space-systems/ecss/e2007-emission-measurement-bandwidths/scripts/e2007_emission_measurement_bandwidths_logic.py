#!/usr/bin/env python3
"""Emission measurement bandwidth logic (ECSS-E-ST-20-07C, 5.2.9.1).

Offline, deterministic, standard-library only. The module fixes the
receiver bandwidth that each emission test frequency range is measured
with, and everything that follows from it:

* the range a measured frequency belongs to, and the bandwidth that
  range prescribes,
* whether the bandwidth a receiver was set to is the prescribed one,
* the coarsest frequency step a sweep may take, expressed as a fraction
  of the bandwidth in force at the point it steps from,
* the shortest dwell a point may be observed for, derived from the
  bandwidth and floored,
* the segments a requested span is broken into where it crosses a range
  boundary, and the point count and sweep time each segment costs,
* per-point and whole-sweep acceptance of a planned or executed run.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "REL_TOL",
    "EMISSION_RANGES",
    "SWEEP_LOWER_HZ",
    "SWEEP_UPPER_HZ",
    "MAX_STEP_FRACTION_OF_BANDWIDTH",
    "DWELL_BANDWIDTH_PRODUCT",
    "MIN_DWELL_FLOOR_S",
    "select_emission_range",
    "prescribed_bandwidth_hz",
    "check_applied_bandwidth",
    "maximum_step_hz",
    "minimum_dwell_s",
    "check_step",
    "check_dwell",
    "span_segments",
    "plan_emission_sweep",
    "evaluate_sweep_point",
    "assess_emission_sweep",
]

# Absorbs binary-representation error when a value computed as a product,
# a quotient or a ceiling lands a few units in the last place outside an
# exactly-met bound. It never widens the bound itself.
REL_TOL = 1e-9

# (lower_hz, upper_hz, prescribed_bandwidth_hz)
# Each emission test frequency range is measured with one bandwidth. The
# bandwidth widens with the range so that the sweep stays affordable while
# the receiver still resolves the emissions the range is looking for.
EMISSION_RANGES = (
    (30.0, 1.0e3, 10.0),
    (1.0e3, 1.0e4, 100.0),
    (1.0e4, 1.5e5, 1.0e3),
    (1.5e5, 3.0e7, 1.0e4),
    (3.0e7, 1.0e9, 1.0e5),
    (1.0e9, 1.8e10, 1.0e6),
)

SWEEP_LOWER_HZ = EMISSION_RANGES[0][0]
SWEEP_UPPER_HZ = EMISSION_RANGES[-1][1]

# A sweep steps by at most this fraction of the bandwidth in force, so no
# emission can fall between two adjacent points unmeasured.
MAX_STEP_FRACTION_OF_BANDWIDTH = 0.5

# A point is observed for at least this many bandwidth time-constants, so
# that the receiver response settles before the level is taken.
DWELL_BANDWIDTH_PRODUCT = 10.0

# Floor under the derived dwell, in seconds. A wide bandwidth would
# otherwise imply a dwell shorter than any receiver can honour.
MIN_DWELL_FLOOR_S = 0.015

_POINT_KEYS = ("id", "frequency_hz", "applied_bandwidth_hz", "dwell_s")


def _finding(code, subject, detail):
    """Build one sweep finding record."""
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


def _at_most(value, limit):
    """Upper-bound comparison that absorbs binary-representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=0.0)


def _at_least(value, limit):
    """Lower-bound comparison that absorbs binary-representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=0.0)


def _same(left, right):
    """Equality that absorbs binary-representation error."""
    return left == right or math.isclose(left, right, rel_tol=REL_TOL, abs_tol=0.0)


def _ceil_with_tolerance(value):
    """Ceiling that does not add a whole step for a last-place remainder."""
    nearest = math.floor(value + 0.5)
    if math.isclose(value, nearest, rel_tol=REL_TOL, abs_tol=REL_TOL):
        return int(nearest)
    return int(math.ceil(value))


def select_emission_range(frequency_hz):
    """Return the emission test frequency range that owns this frequency."""
    frequency = _as_positive_float(frequency_hz, "frequency_hz")
    if frequency < SWEEP_LOWER_HZ or frequency > SWEEP_UPPER_HZ:
        raise ValueError(
            "frequency %r lies outside the emission range %r to %r Hz"
            % (frequency, SWEEP_LOWER_HZ, SWEEP_UPPER_HZ)
        )
    for lower, upper, bandwidth in EMISSION_RANGES:
        if lower <= frequency <= upper:
            return {
                "lower_hz": lower,
                "upper_hz": upper,
                "bandwidth_hz": bandwidth,
            }
    raise ValueError("no emission range covers frequency %r Hz" % (frequency,))


def prescribed_bandwidth_hz(frequency_hz):
    """Receiver bandwidth prescribed at this frequency, in hertz."""
    return select_emission_range(frequency_hz)["bandwidth_hz"]


def check_applied_bandwidth(frequency_hz, applied_bandwidth_hz):
    """Check the bandwidth a receiver was set to against the prescribed one."""
    applied = _as_positive_float(applied_bandwidth_hz, "applied_bandwidth_hz")
    band = select_emission_range(frequency_hz)
    prescribed = band["bandwidth_hz"]
    return {
        "quantity": "bandwidth",
        "frequency_hz": _as_positive_float(frequency_hz, "frequency_hz"),
        "applied_hz": applied,
        "prescribed_hz": prescribed,
        "ratio": applied / prescribed,
        "range": band,
        "as_prescribed": _same(applied, prescribed),
    }


def maximum_step_hz(frequency_hz, fraction=MAX_STEP_FRACTION_OF_BANDWIDTH):
    """Coarsest step a sweep may take from this frequency, in hertz."""
    share = _as_positive_float(fraction, "fraction")
    if share > 1.0:
        raise ValueError("fraction must not exceed one, got %r" % (fraction,))
    return prescribed_bandwidth_hz(frequency_hz) * share


def minimum_dwell_s(
    frequency_hz, product=DWELL_BANDWIDTH_PRODUCT, floor_s=MIN_DWELL_FLOOR_S
):
    """Shortest dwell this frequency's bandwidth allows, in seconds."""
    cycles = _as_positive_float(product, "product")
    floor = _as_positive_float(floor_s, "floor_s")
    bandwidth = prescribed_bandwidth_hz(frequency_hz)
    return max(cycles / bandwidth, floor)


def check_step(previous_hz, next_hz):
    """Check the step between two adjacent sweep points."""
    previous = _as_positive_float(previous_hz, "previous_hz")
    following = _as_positive_float(next_hz, "next_hz")
    if following <= previous:
        raise ValueError(
            "a sweep step must increase in frequency: %r does not follow %r"
            % (next_hz, previous_hz)
        )
    allowed = maximum_step_hz(previous)
    step = following - previous
    return {
        "quantity": "step",
        "previous_hz": previous,
        "next_hz": following,
        "step_hz": step,
        "allowed_hz": allowed,
        "within": _at_most(step, allowed),
    }


def check_dwell(frequency_hz, dwell_s):
    """Check that a sweep point is observed for long enough."""
    dwell = _as_positive_float(dwell_s, "dwell_s")
    required = minimum_dwell_s(frequency_hz)
    return {
        "quantity": "dwell",
        "frequency_hz": _as_positive_float(frequency_hz, "frequency_hz"),
        "dwell_s": dwell,
        "required_s": required,
        "within": _at_least(dwell, required),
    }


def span_segments(lower_hz, upper_hz):
    """Break a requested span at every range boundary it crosses."""
    lower = _as_positive_float(lower_hz, "lower_hz")
    upper = _as_positive_float(upper_hz, "upper_hz")
    if upper <= lower:
        raise ValueError(
            "span must ascend: %r does not exceed %r" % (upper_hz, lower_hz)
        )
    if lower < SWEEP_LOWER_HZ or upper > SWEEP_UPPER_HZ:
        raise ValueError(
            "span %r to %r Hz leaves the emission range %r to %r Hz"
            % (lower_hz, upper_hz, SWEEP_LOWER_HZ, SWEEP_UPPER_HZ)
        )
    segments = []
    for range_lower, range_upper, bandwidth in EMISSION_RANGES:
        start = max(lower, range_lower)
        stop = min(upper, range_upper)
        if stop <= start:
            continue
        segments.append(
            {
                "lower_hz": start,
                "upper_hz": stop,
                "bandwidth_hz": bandwidth,
                "span_hz": stop - start,
            }
        )
    if not segments:
        raise ValueError(
            "span %r to %r Hz resolves to no measurable segment" % (lower_hz, upper_hz)
        )
    return segments


def plan_emission_sweep(lower_hz, upper_hz):
    """Cost a requested span: segments, point counts and sweep time."""
    segments = span_segments(lower_hz, upper_hz)
    planned = []
    total_points = 0
    total_seconds = 0.0
    for segment in segments:
        step = segment["bandwidth_hz"] * MAX_STEP_FRACTION_OF_BANDWIDTH
        dwell = max(
            DWELL_BANDWIDTH_PRODUCT / segment["bandwidth_hz"], MIN_DWELL_FLOOR_S
        )
        intervals = _ceil_with_tolerance(segment["span_hz"] / step)
        points = intervals + 1
        seconds = points * dwell
        planned.append(
            {
                "lower_hz": segment["lower_hz"],
                "upper_hz": segment["upper_hz"],
                "bandwidth_hz": segment["bandwidth_hz"],
                "span_hz": segment["span_hz"],
                "step_hz": step,
                "dwell_s": dwell,
                "point_count": points,
                "seconds": seconds,
            }
        )
        total_points += points
        total_seconds += seconds
    return {
        "lower_hz": planned[0]["lower_hz"],
        "upper_hz": planned[-1]["upper_hz"],
        "segments": planned,
        "segment_count": len(planned),
        "point_count": total_points,
        "seconds": total_seconds,
    }


def evaluate_sweep_point(point):
    """Evaluate one sweep point against the bandwidth its range prescribes."""
    if not isinstance(point, dict):
        raise ValueError("point must be a mapping, got %s" % type(point).__name__)
    unknown = [key for key in point if key not in _POINT_KEYS]
    if unknown:
        raise ValueError(
            "point carries unknown key(s): %s" % ", ".join(sorted(unknown))
        )
    for key in ("id", "frequency_hz", "applied_bandwidth_hz"):
        if key not in point:
            raise ValueError("point is missing required key %r" % key)
    if not isinstance(point["id"], str) or not point["id"].strip():
        raise ValueError("point id must be a non-blank string")
    identifier = point["id"].strip()
    checks = {
        "bandwidth": check_applied_bandwidth(
            point["frequency_hz"], point["applied_bandwidth_hz"]
        )
    }
    findings = []
    if not checks["bandwidth"]["as_prescribed"]:
        findings.append(
            _finding(
                "bandwidth-not-as-prescribed",
                identifier,
                "receiver set to %.6g Hz where the range prescribes %.6g Hz"
                % (
                    checks["bandwidth"]["applied_hz"],
                    checks["bandwidth"]["prescribed_hz"],
                ),
            )
        )
    if "dwell_s" in point:
        checks["dwell"] = check_dwell(point["frequency_hz"], point["dwell_s"])
        if not checks["dwell"]["within"]:
            findings.append(
                _finding(
                    "dwell-too-short",
                    identifier,
                    "observed %.5f s against the %.5f s its bandwidth requires"
                    % (checks["dwell"]["dwell_s"], checks["dwell"]["required_s"]),
                )
            )
    return {
        "id": identifier,
        "frequency_hz": checks["bandwidth"]["frequency_hz"],
        "checks": checks,
        "findings": findings,
        "conforming": not findings,
    }


def assess_emission_sweep(points):
    """Assess an executed emission sweep point by point and as a whole."""
    if isinstance(points, (str, bytes)) or not hasattr(points, "__iter__"):
        raise ValueError("points must be an iterable of sweep points")
    evaluated = [evaluate_sweep_point(point) for point in points]
    if not evaluated:
        raise ValueError("a sweep must contain at least one point")
    seen = set()
    for record in evaluated:
        if record["id"] in seen:
            raise ValueError("sweep point %r appears twice" % record["id"])
        seen.add(record["id"])
    findings = []
    for record in evaluated:
        findings.extend(record["findings"])
    steps = []
    previous = None
    for record in evaluated:
        current = record["frequency_hz"]
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
                step = check_step(previous, current)
                steps.append(step)
                if not step["within"]:
                    findings.append(
                        _finding(
                            "step-too-coarse",
                            record["id"],
                            "stepped %.6g Hz from %.6g Hz, above the %.6g Hz its "
                            "bandwidth allows"
                            % (step["step_hz"], previous, step["allowed_hz"]),
                        )
                    )
        previous = current
    covered = plan_emission_sweep(
        evaluated[0]["frequency_hz"], evaluated[-1]["frequency_hz"]
    ) if len(evaluated) > 1 and evaluated[-1]["frequency_hz"] > evaluated[0][
        "frequency_hz"
    ] else None
    if covered is not None and len(evaluated) < covered["point_count"]:
        findings.append(
            _finding(
                "sweep-under-sampled",
                "emission-sweep",
                "%d point(s) taken where the bandwidths require %d across the "
                "same span" % (len(evaluated), covered["point_count"]),
            )
        )
    accepted = not findings
    return {
        "verdict": "conforming" if accepted else "non-conforming",
        "accepted": accepted,
        "points": evaluated,
        "point_count": len(evaluated),
        "step_count": len(steps),
        "required_plan": covered,
        "findings": findings,
        "conforming_fraction": sum(1 for r in evaluated if r["conforming"])
        / float(len(evaluated)),
    }
