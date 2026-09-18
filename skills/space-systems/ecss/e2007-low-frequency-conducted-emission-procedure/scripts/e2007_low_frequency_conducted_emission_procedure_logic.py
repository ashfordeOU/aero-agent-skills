#!/usr/bin/env python3
"""Low-frequency conducted-emission procedure, ECSS-E-ST-20-07C 5.4.2.4.

Paraphrased procedure, no verbatim standard text. The clause walks the run
from switching the instruments on to writing the record down: the receiver
and the source warm up, a system check injects a known current and confirms
the chain reads it back, then the band is swept and recorded. This module
turns that walk into a deterministic plan and verdict:

  step records   -> mandatory steps present, in order
  warm-up        -> elapsed against the required soak
  system check   -> read-back error against the tolerance
  sweep plan     -> step size and dwell against the resolution bandwidth
  scan time      -> steps * dwell, against the time allowed

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibel comparison tolerance. Read-back errors are differences of float
# levels, so an exactly-met tolerance can land a few units in the last place
# outside. It absorbs representation error only; it never widens a tolerance.
DB_TOL = 1e-9

# Generic relative tolerance for time and frequency comparisons.
REL_TOL = 1e-12

# Soak the receiver and the source need before the first reading, minutes.
DEFAULT_WARMUP_MINUTES = 30.0

# Largest acceptable difference between the level the system check injects
# and the level the chain reads back, decibels.
DEFAULT_SYSTEM_CHECK_TOLERANCE_DB = 3.0

# Largest tuning step as a fraction of the resolution bandwidth. Stepping
# wider than this walks past narrowband emissions between measured points.
DEFAULT_STEP_FRACTION = 0.5

# Smallest dwell per measured point, as a multiple of the reciprocal of the
# resolution bandwidth. A shorter dwell reads the filter before it settles.
DEFAULT_DWELL_BANDWIDTH_PRODUCT = 1.0

STEP_WARMUP = "warm-up"
STEP_SYSTEM_CHECK = "system-check"
STEP_AMBIENT_CHECK = "ambient-check"
STEP_RECORDING = "recording"
STEP_POST_CHECK = "post-check"
MANDATORY_STEPS = (
    STEP_WARMUP,
    STEP_SYSTEM_CHECK,
    STEP_AMBIENT_CHECK,
    STEP_RECORDING,
    STEP_POST_CHECK,
)

VERDICT_VALID = "procedure-valid"
VERDICT_REJECTED = "procedure-rejected"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def at_most(value, limit, tol=DB_TOL):
    """True when value stays within the limit, absorbing float error only."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=tol)


def at_least(value, requirement, tol=DB_TOL):
    """True when value meets the requirement, absorbing float error only."""
    if value >= requirement:
        return True
    return math.isclose(value, requirement, rel_tol=0.0, abs_tol=tol)


def normalize_step(step):
    """Return the recognized procedure step for a raw step name."""
    if not isinstance(step, str):
        raise ValueError("procedure step must be a string, got %r" % (step,))
    key = step.strip().lower()
    if key not in MANDATORY_STEPS:
        raise ValueError(
            "unrecognized procedure step %r; recognized: %s"
            % (step, ", ".join(MANDATORY_STEPS))
        )
    return key


def sequence_steps(steps):
    """Order a list of executed steps and report what is absent or swapped."""
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps: must be a list of step names")
    if len(steps) == 0:
        raise ValueError("steps: at least one executed step is required")
    seen = []
    for raw in steps:
        step = normalize_step(raw)
        if step in seen:
            raise ValueError("steps: step %r appears twice" % step)
        seen.append(step)
    missing = [step for step in MANDATORY_STEPS if step not in seen]
    expected = [step for step in MANDATORY_STEPS if step in seen]
    out_of_order = seen != expected
    return {
        "executed": seen,
        "expected_order": expected,
        "missing": missing,
        "out_of_order": out_of_order,
    }


def warmup_headroom_minutes(elapsed_minutes, required_minutes=DEFAULT_WARMUP_MINUTES):
    """Minutes of soak beyond the required warm-up; negative when short."""
    elapsed = _number({"v": elapsed_minutes}, "v", "elapsed_minutes")
    required = _number({"v": required_minutes}, "v", "required_minutes")
    if elapsed < 0.0:
        raise ValueError("elapsed_minutes must be >= 0, got %g" % elapsed)
    if required <= 0.0:
        raise ValueError("required_minutes must be > 0, got %g" % required)
    return elapsed - required


def system_check_error_db(injected_dbuv, read_back_dbuv):
    """Magnitude of the read-back error of the injected calibration level."""
    injected = _number({"v": injected_dbuv}, "v", "injected_dbuv")
    read_back = _number({"v": read_back_dbuv}, "v", "read_back_dbuv")
    return abs(read_back - injected)


def maximum_step_hz(bandwidth_hz, fraction=DEFAULT_STEP_FRACTION):
    """Largest tuning step that still samples a narrowband emission."""
    bandwidth = _number({"v": bandwidth_hz}, "v", "bandwidth_hz")
    share = _number({"v": fraction}, "v", "fraction")
    if bandwidth <= 0.0:
        raise ValueError("bandwidth_hz must be > 0, got %g" % bandwidth)
    if not 0.0 < share <= 1.0:
        raise ValueError("fraction must lie in (0, 1], got %g" % share)
    return bandwidth * share


def minimum_dwell_s(bandwidth_hz, product=DEFAULT_DWELL_BANDWIDTH_PRODUCT):
    """Shortest dwell per point that lets the resolution filter settle."""
    bandwidth = _number({"v": bandwidth_hz}, "v", "bandwidth_hz")
    factor = _number({"v": product}, "v", "product")
    if bandwidth <= 0.0:
        raise ValueError("bandwidth_hz must be > 0, got %g" % bandwidth)
    if factor <= 0.0:
        raise ValueError("product must be > 0, got %g" % factor)
    return factor / bandwidth


def measured_points(band_hz, step_hz):
    """Number of measured points a stepped sweep of the band produces."""
    if not isinstance(band_hz, (list, tuple)) or len(band_hz) != 2:
        raise ValueError("band_hz: must be a (low_hz, high_hz) pair")
    low = _number({"v": band_hz[0]}, "v", "band_hz.low")
    high = _number({"v": band_hz[1]}, "v", "band_hz.high")
    step = _number({"v": step_hz}, "v", "step_hz")
    if low <= 0.0:
        raise ValueError("band_hz.low must be > 0, got %g" % low)
    if high <= low:
        raise ValueError("band_hz.high %g must exceed low %g" % (high, low))
    if step <= 0.0:
        raise ValueError("step_hz must be > 0, got %g" % step)
    span = high - low
    return int(math.floor(span / step + REL_TOL)) + 1


def scan_time_s(band_hz, step_hz, dwell_s):
    """Total time the stepped sweep occupies, seconds."""
    dwell = _number({"v": dwell_s}, "v", "dwell_s")
    if dwell <= 0.0:
        raise ValueError("dwell_s must be > 0, got %g" % dwell)
    return measured_points(band_hz, step_hz) * dwell


def validate_sweep_plan(
    plan,
    step_fraction=DEFAULT_STEP_FRACTION,
    dwell_product=DEFAULT_DWELL_BANDWIDTH_PRODUCT,
):
    """Validate the stepped-sweep plan and return a normalized record."""
    if not isinstance(plan, dict):
        raise ValueError("sweep_plan: record must be a mapping")
    where = "sweep_plan"
    low = _number(plan, "band_low_hz", where)
    high = _number(plan, "band_high_hz", where)
    if low <= 0.0:
        raise ValueError("%s: band_low_hz must be > 0, got %g" % (where, low))
    if high <= low:
        raise ValueError(
            "%s: band_high_hz %g must exceed band_low_hz %g" % (where, high, low)
        )
    bandwidth = _number(plan, "bandwidth_hz", where)
    if bandwidth <= 0.0:
        raise ValueError("%s: bandwidth_hz must be > 0, got %g" % (where, bandwidth))
    step = _number(plan, "step_hz", where)
    if step <= 0.0:
        raise ValueError("%s: step_hz must be > 0, got %g" % (where, step))
    dwell = _number(plan, "dwell_s", where)
    if dwell <= 0.0:
        raise ValueError("%s: dwell_s must be > 0, got %g" % (where, dwell))
    step_ceiling = maximum_step_hz(bandwidth, step_fraction)
    dwell_floor = minimum_dwell_s(bandwidth, dwell_product)
    points = measured_points((low, high), step)
    return {
        "band_hz": (low, high),
        "bandwidth_hz": bandwidth,
        "step_hz": step,
        "step_ceiling_hz": step_ceiling,
        "step_ok": at_most(step, step_ceiling, tol=step_ceiling * REL_TOL),
        "dwell_s": dwell,
        "dwell_floor_s": dwell_floor,
        "dwell_ok": at_least(dwell, dwell_floor, tol=dwell_floor * REL_TOL),
        "points": points,
        "scan_time_s": points * dwell,
    }


def assess_procedure(
    steps,
    warmup_minutes,
    system_check,
    sweep_plan,
    required_warmup_minutes=DEFAULT_WARMUP_MINUTES,
    system_check_tolerance_db=DEFAULT_SYSTEM_CHECK_TOLERANCE_DB,
    allowed_scan_time_s=None,
    step_fraction=DEFAULT_STEP_FRACTION,
    dwell_product=DEFAULT_DWELL_BANDWIDTH_PRODUCT,
):
    """Full clause 5.4.2.4 assessment of one conducted-emission run."""
    sequence = sequence_steps(steps)
    headroom = warmup_headroom_minutes(warmup_minutes, required_warmup_minutes)
    if not isinstance(system_check, dict):
        raise ValueError("system_check: record must be a mapping")
    tolerance = _number(
        {"v": system_check_tolerance_db}, "v", "system_check_tolerance_db"
    )
    if tolerance <= 0.0:
        raise ValueError("system_check_tolerance_db must be > 0, got %g" % tolerance)
    error = system_check_error_db(
        _number(system_check, "injected_dbuv", "system_check"),
        _number(system_check, "read_back_dbuv", "system_check"),
    )
    plan = validate_sweep_plan(sweep_plan, step_fraction, dwell_product)

    findings = []
    limitations = []
    for step in sequence["missing"]:
        findings.append("mandatory step not executed: %s" % step)
    if sequence["out_of_order"]:
        findings.append(
            "steps executed out of order: %s" % ", ".join(sequence["executed"])
        )
    if headroom < 0.0 and not math.isclose(headroom, 0.0, rel_tol=0.0, abs_tol=DB_TOL):
        findings.append(
            "warm-up short by %.1f minute(s) of the %g required"
            % (-headroom, required_warmup_minutes)
        )
    elif headroom <= required_warmup_minutes * 0.1:
        limitations.append(
            "warm-up left only %.1f minute(s) of margin" % headroom
        )
    if not at_most(error, tolerance):
        findings.append(
            "system check read back %.2f dB from the injected level, past the "
            "%g dB tolerance" % (error, tolerance)
        )
    if not plan["step_ok"]:
        findings.append(
            "tuning step %g Hz is wider than the %g Hz ceiling for a %g Hz "
            "bandwidth" % (plan["step_hz"], plan["step_ceiling_hz"], plan["bandwidth_hz"])
        )
    if not plan["dwell_ok"]:
        findings.append(
            "dwell %g s is shorter than the %g s the %g Hz bandwidth needs"
            % (plan["dwell_s"], plan["dwell_floor_s"], plan["bandwidth_hz"])
        )
    if allowed_scan_time_s is not None:
        allowed = _number({"v": allowed_scan_time_s}, "v", "allowed_scan_time_s")
        if allowed <= 0.0:
            raise ValueError("allowed_scan_time_s must be > 0, got %g" % allowed)
        if not at_most(plan["scan_time_s"], allowed, tol=allowed * REL_TOL):
            findings.append(
                "scan needs %.1f s, beyond the %g s allowed for the run"
                % (plan["scan_time_s"], allowed)
            )

    return {
        "sequence": sequence,
        "warmup_headroom_minutes": headroom,
        "system_check_error_db": error,
        "system_check_tolerance_db": tolerance,
        "sweep_plan": plan,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_VALID if not findings else VERDICT_REJECTED,
    }
