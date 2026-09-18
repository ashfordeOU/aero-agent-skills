#!/usr/bin/env python3
"""Radiated magnetic susceptibility procedure, ECSS-E-ST-20-07C 5.4.10.4.

Paraphrased procedure, no verbatim standard text. The clause walks a magnetic
exposure run from switching the instruments on, through the check that proves
the loop is radiating what the drive says, to the stepped sweep applied with
the radiating loop and the search for the level at which the unit reacts:

  executed steps  -> step normalization, absences and order
  instrument soak -> headroom against the required warm-up
  verification    -> read-back error against its decibel tolerance
  band + step     -> tuned point count, dwell floor and sweep time
  reaction level  -> threshold search depth and the margin it leaves

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibel comparison tolerance. Levels are ratios of float quantities passed
# through a logarithm, so an exactly-met tolerance can land a few units in the
# last place outside it. The tolerance absorbs representation error only.
DB_TOL = 1e-9

# Time comparison tolerance, same reasoning on the duration side.
TIME_REL_TOL = 1e-12

# Required exposure band, hertz.
DEFAULT_BAND_HZ = (30.0, 100.0e3)

# Soak the source, the amplifier and the monitoring chain need from cold,
# minutes.
DEFAULT_WARM_UP_MINUTES = 30.0

# Decibel tolerance the system verification read-back is graded against.
DEFAULT_VERIFICATION_TOLERANCE_DB = 3.0

# Largest tuning step as a fraction of the tuned frequency.
DEFAULT_STEP_FRACTION = 0.05

# Whole cycles of the tuned frequency a dwell must span before a reaction can
# be believed absent.
DEFAULT_DWELL_CYCLES = 10.0

# Level reduction per step during the threshold search, decibel.
DEFAULT_THRESHOLD_STEP_DB = 2.0

VERDICT_VALID = "run-valid"
VERDICT_INVALID = "run-invalid"

# The clause's step order. Order carries meaning: a verification after the
# sweep proves the chain was healthy at the end, not while the data was taken.
ORDERED_STEPS = (
    "instrument-warm-up",
    "system-verification",
    "monitor-baseline",
    "loop-placement",
    "stepped-exposure-sweep",
    "threshold-search",
    "post-run-verification",
)


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


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _positive(value, name):
    number = _scalar(value, name)
    if number <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, number))
    return number


def _at_least(value, bound, rel_tol=TIME_REL_TOL):
    """True when value reaches a lower bound, absorbing float error only."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=rel_tol, abs_tol=0.0)


def _at_most(value, bound, rel_tol=TIME_REL_TOL):
    """True when value stays under an upper bound, absorbing float error only."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=rel_tol, abs_tol=0.0)


def _ceil_steps(ratio):
    """Whole steps spanning a ratio, with an exact fit left un-rounded up.

    math.log is not correctly rounded, so a span that divides exactly can come
    back a unit in the last place high and tip math.ceil to the next integer.
    The tolerance keeps an exact fit an exact fit.
    """
    nearest = round(ratio)
    if nearest >= 0 and math.isclose(ratio, nearest, rel_tol=1e-9, abs_tol=1e-12):
        return int(nearest)
    return int(math.ceil(ratio))


def normalize_step(step):
    """Return the recognized procedure step for a raw step designation."""
    if not isinstance(step, str):
        raise ValueError("procedure step must be a string, got %r" % (step,))
    key = step.strip().lower()
    if key not in ORDERED_STEPS:
        raise ValueError(
            "unrecognized procedure step %r; recognized: %s"
            % (step, ", ".join(ORDERED_STEPS))
        )
    return key


def validate_band(band, where="band"):
    """Validate a (low, high) frequency band and return it as floats."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s: band must be a (low_hz, high_hz) pair" % where)
    low = _scalar(band[0], "%s.low_hz" % where)
    high = _scalar(band[1], "%s.high_hz" % where)
    if low <= 0.0:
        raise ValueError("%s: low_hz must be > 0, got %g" % (where, low))
    if high <= low:
        raise ValueError("%s: high_hz %g must exceed low_hz %g" % (where, high, low))
    return (low, high)


def sequence_report(steps):
    """Reduce the executed steps to the absent ones and whether order held."""
    if not isinstance(steps, (list, tuple)) or len(steps) == 0:
        raise ValueError("steps: at least one executed step is required")
    executed = []
    for step in steps:
        key = normalize_step(step)
        if key in executed:
            raise ValueError(
                "steps: step %r executed twice; each is executed once" % key
            )
        executed.append(key)
    missing = [step for step in ORDERED_STEPS if step not in executed]
    positions = [ORDERED_STEPS.index(step) for step in executed]
    in_order = positions == sorted(positions)
    out_of_order = []
    if not in_order:
        for index in range(1, len(executed)):
            if positions[index] < positions[index - 1]:
                out_of_order.append((executed[index - 1], executed[index]))
    return {
        "executed": executed,
        "missing": missing,
        "in_order": in_order,
        "inversions": out_of_order,
    }


def warm_up_report(soak_minutes, required_minutes=DEFAULT_WARM_UP_MINUTES):
    """Compare the instrument soak with the required warm-up and keep headroom."""
    soak = _scalar(soak_minutes, "soak_minutes")
    if soak < 0.0:
        raise ValueError("soak_minutes must be >= 0, got %g" % soak)
    required = _positive(required_minutes, "required_minutes")
    return {
        "soak_minutes": soak,
        "required_minutes": required,
        "headroom_minutes": soak - required,
        "satisfied": _at_least(soak, required),
    }


def verification_error_db(measured_flux_t, reference_flux_t):
    """Magnitude of the system verification read-back error, decibel.

    The comparison is on the magnitude, so a chain radiating high fails on the
    same footing as one radiating low.
    """
    measured = _positive(measured_flux_t, "measured_flux_t")
    reference = _positive(reference_flux_t, "reference_flux_t")
    return abs(20.0 * math.log10(measured / reference))


def frequency_step_count(band=DEFAULT_BAND_HZ, step_fraction=DEFAULT_STEP_FRACTION):
    """Tuned points a proportional step covers the band in."""
    low, high = validate_band(band, "band")
    fraction = _positive(step_fraction, "step_fraction")
    if fraction >= 1.0:
        raise ValueError("step_fraction must be < 1, got %g" % fraction)
    spans = math.log(high / low) / math.log(1.0 + fraction)
    return _ceil_steps(spans) + 1


def dwell_floor_s(
    frequency_hz, monitor_response_s, cycles=DEFAULT_DWELL_CYCLES
):
    """Shortest dwell at a tuned point that can support an absent reaction.

    The dwell has to outlast both the monitored function's own response and a
    whole number of cycles of the tuned frequency, whichever is longer.
    """
    frequency = _positive(frequency_hz, "frequency_hz")
    response = _scalar(monitor_response_s, "monitor_response_s")
    if response < 0.0:
        raise ValueError("monitor_response_s must be >= 0, got %g" % response)
    count = _positive(cycles, "cycles")
    return max(response, count / frequency)


def sweep_time_s(points, dwell_s):
    """Time a stepped sweep occupies at a given dwell per point."""
    count = _scalar(points, "points")
    if count < 1.0:
        raise ValueError("points must be >= 1, got %g" % count)
    if abs(count - round(count)) > 1e-9:
        raise ValueError("points must be a whole number, got %g" % count)
    dwell = _positive(dwell_s, "dwell_s")
    return float(round(count)) * dwell


def threshold_reduction_steps(
    applied_flux_t, threshold_flux_t, step_db=DEFAULT_THRESHOLD_STEP_DB
):
    """Reduction steps between the applied level and the reaction threshold."""
    applied = _positive(applied_flux_t, "applied_flux_t")
    threshold = _positive(threshold_flux_t, "threshold_flux_t")
    step = _positive(step_db, "step_db")
    if threshold > applied and not math.isclose(
        threshold, applied, rel_tol=1e-12, abs_tol=0.0
    ):
        raise ValueError(
            "threshold_flux_t %g cannot exceed the applied level %g"
            % (threshold, applied)
        )
    drop_db = 20.0 * math.log10(applied / threshold)
    return _ceil_steps(drop_db / step)


def susceptibility_margin_db(threshold_flux_t, required_flux_t):
    """Margin the reaction threshold leaves over the required exposure level."""
    threshold = _positive(threshold_flux_t, "threshold_flux_t")
    required = _positive(required_flux_t, "required_flux_t")
    return 20.0 * math.log10(threshold / required)


def assess_procedure(
    steps,
    soak_minutes,
    measured_flux_t,
    reference_flux_t,
    band=DEFAULT_BAND_HZ,
    step_fraction=DEFAULT_STEP_FRACTION,
    planned_dwell_s=1.0,
    monitor_response_s=0.2,
    required_warm_up_minutes=DEFAULT_WARM_UP_MINUTES,
    verification_tolerance_db=DEFAULT_VERIFICATION_TOLERANCE_DB,
    allowed_sweep_time_s=None,
    threshold_flux_t=None,
    required_flux_t=None,
):
    """Full clause 5.4.10.4 assessment of one radiated magnetic exposure run."""
    required_band = validate_band(band, "band")
    tolerance = _positive(verification_tolerance_db, "verification_tolerance_db")
    dwell = _positive(planned_dwell_s, "planned_dwell_s")

    findings = []
    limitations = []

    sequence = sequence_report(steps)
    for step in sequence["missing"]:
        findings.append("mandatory step never executed: %s" % step)
    for earlier, later in sequence["inversions"]:
        findings.append("step %s was executed before %s" % (later, earlier))

    warm_up = warm_up_report(soak_minutes, required_warm_up_minutes)
    if not warm_up["satisfied"]:
        findings.append(
            "instruments soaked %g min against the %g min warm-up"
            % (warm_up["soak_minutes"], warm_up["required_minutes"])
        )
    elif warm_up["headroom_minutes"] < 5.0:
        limitations.append(
            "warm-up headroom is only %g min" % warm_up["headroom_minutes"]
        )

    error_db = verification_error_db(measured_flux_t, reference_flux_t)
    if not _at_most(error_db, tolerance, rel_tol=0.0) and not math.isclose(
        error_db, tolerance, rel_tol=0.0, abs_tol=DB_TOL
    ):
        findings.append(
            "system verification read-back is %.2f dB out against a %.2f dB "
            "tolerance" % (error_db, tolerance)
        )
    elif error_db > tolerance * 0.75:
        limitations.append(
            "system verification read-back is %.2f dB out, inside but near the "
            "%.2f dB tolerance" % (error_db, tolerance)
        )

    points = frequency_step_count(required_band, step_fraction)
    floor = dwell_floor_s(required_band[0], monitor_response_s)
    if not _at_least(dwell, floor):
        findings.append(
            "planned dwell %g s is under the %g s floor at the bottom of the band"
            % (dwell, floor)
        )
    sweep = sweep_time_s(points, dwell)
    if allowed_sweep_time_s is not None:
        allowed = _positive(allowed_sweep_time_s, "allowed_sweep_time_s")
        if not _at_most(sweep, allowed):
            findings.append(
                "sweep occupies %g s against the %g s the run is allowed"
                % (sweep, allowed)
            )
        elif sweep > allowed * 0.9:
            limitations.append(
                "sweep occupies %g s of the %g s allowed" % (sweep, allowed)
            )

    threshold_report = None
    if threshold_flux_t is not None:
        if required_flux_t is None:
            raise ValueError(
                "required_flux_t is needed to grade a reaction threshold"
            )
        applied = _positive(measured_flux_t, "measured_flux_t")
        reductions = threshold_reduction_steps(applied, threshold_flux_t)
        margin = susceptibility_margin_db(threshold_flux_t, required_flux_t)
        threshold_report = {
            "threshold_flux_t": _positive(threshold_flux_t, "threshold_flux_t"),
            "reduction_steps": reductions,
            "margin_db": margin,
        }
        if margin < 0.0 and not math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=DB_TOL):
            findings.append(
                "unit reacts %.2f dB below the required exposure level" % abs(margin)
            )
        elif margin < 6.0:
            limitations.append(
                "reaction threshold leaves only %.2f dB over the required level"
                % margin
            )

    return {
        "sequence": sequence,
        "warm_up": warm_up,
        "verification_error_db": error_db,
        "tuned_points": points,
        "dwell_floor_s": floor,
        "planned_dwell_s": dwell,
        "sweep_time_s": sweep,
        "threshold": threshold_report,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_VALID if not findings else VERDICT_INVALID,
    }
