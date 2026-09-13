#!/usr/bin/env python3
"""Pre-run scattering-parameter gate at the test site (ECSS-E-ST-20-01C 8.4).

Deterministic, offline, python3 standard library only. The clause intent is
paraphrased into implementable logic; no standard text is reproduced.

With the article mounted in the multipactor bed and the drive still low, the
sweep is screened four ways: the frequency grid is admissible, every point is
passive and in range, every point reproduces the component-level reference
inside a decibel tolerance, and every point respects the absolute return-loss
and insertion-loss limits of the test specification.
"""

from __future__ import annotations

import math

#: Relative tolerance absorbing binary-floating-point representation error on
#: an exact-limit comparison. It never widens an engineering limit.
REL_TOL = 1e-9

#: Absolute tolerance for a comparison whose operands may be near zero.
ABS_TOL = 1e-12

#: A magnitude may not exceed unity for a passive article.
UNIT_MAGNITUDE = 1.0


# ----------------------------------------------------------------------------
# Frequency grid
# ----------------------------------------------------------------------------

def validate_frequency_grid(points_hz, band_low_hz, band_high_hz, min_points):
    """Check the sweep grid is ordered, unique and covers the declared band.

    Raises ValueError for a structurally broken grid (empty, non-numeric,
    unordered, duplicated, or a band whose edges are not ordered). Short
    coverage and a sparse grid are findings, not errors: the sweep happened,
    it simply does not clear the gate.
    """
    if not isinstance(points_hz, (list, tuple)):
        raise ValueError("points_hz must be a list or tuple")
    if not points_hz:
        raise ValueError("points_hz must not be empty")
    if not isinstance(min_points, int) or isinstance(min_points, bool):
        raise ValueError("min_points must be an int, got %r" % (min_points,))
    if min_points < 2:
        raise ValueError("min_points must be at least 2, got %r" % (min_points,))

    edges = []
    for name, value in (("band_low_hz", band_low_hz), ("band_high_hz", band_high_hz)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a number, got %r" % (name, value))
        out = float(value)
        if not math.isfinite(out) or out <= 0.0:
            raise ValueError("%s must be finite and strictly positive" % name)
        edges.append(out)
    low, high = edges
    if not low < high:
        raise ValueError("band_low_hz must be strictly below band_high_hz")

    grid = []
    for value in points_hz:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("frequency point must be a number, got %r" % (value,))
        out = float(value)
        if not math.isfinite(out) or out <= 0.0:
            raise ValueError("frequency point must be finite and positive: %r" % (value,))
        if grid and out == grid[-1]:
            raise ValueError("duplicate frequency point: %r" % (value,))
        if grid and out < grid[-1]:
            raise ValueError("frequency grid must be strictly increasing at %r" % (value,))
        grid.append(out)

    findings = []
    covers_low = grid[0] <= low or math.isclose(grid[0], low, rel_tol=REL_TOL)
    covers_high = grid[-1] >= high or math.isclose(grid[-1], high, rel_tol=REL_TOL)
    if not covers_low:
        findings.append(
            "grid starts at %.6g Hz, above the declared band edge %.6g Hz" % (grid[0], low)
        )
    if not covers_high:
        findings.append(
            "grid ends at %.6g Hz, below the declared band edge %.6g Hz" % (grid[-1], high)
        )
    in_band = [f for f in grid if low <= f <= high]
    if len(in_band) < min_points:
        findings.append(
            "grid carries %d in-band point(s), fewer than the %d required"
            % (len(in_band), min_points)
        )
    return {
        "points": grid,
        "in_band_points": len(in_band),
        "covers_band": covers_low and covers_high,
        "compliant": not findings,
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# Magnitude conversions
# ----------------------------------------------------------------------------

def _magnitude(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    if out > UNIT_MAGNITUDE and not math.isclose(
        out, UNIT_MAGNITUDE, rel_tol=REL_TOL, abs_tol=ABS_TOL
    ):
        raise ValueError(
            "%s exceeds unity (%r): a passive article cannot reflect or "
            "transmit more than the incident wave" % (label, value)
        )
    return min(out, UNIT_MAGNITUDE)


def return_loss_db(reflection_magnitude):
    """Return the return-loss in decibel for a reflection-coefficient magnitude.

    A perfectly matched port reflects nothing and has unbounded return-loss.
    """
    magnitude = _magnitude(reflection_magnitude, "reflection_magnitude")
    if magnitude == 0.0:
        return math.inf
    return -20.0 * math.log10(magnitude)


def vswr_from_reflection(reflection_magnitude):
    """Return the voltage-standing-wave-ratio for a reflection magnitude."""
    magnitude = _magnitude(reflection_magnitude, "reflection_magnitude")
    if magnitude == UNIT_MAGNITUDE:
        return math.inf
    return (1.0 + magnitude) / (1.0 - magnitude)


def insertion_loss_db(transmission_magnitude):
    """Return the insertion-loss in decibel for a transmission magnitude.

    A fully blocked path transmits nothing and has unbounded insertion-loss.
    """
    magnitude = _magnitude(transmission_magnitude, "transmission_magnitude")
    if magnitude == 0.0:
        return math.inf
    return -20.0 * math.log10(magnitude)


def check_passivity(reflection_magnitude, transmission_magnitude):
    """Check the two magnitudes describe a passive two-port.

    The squares are fractions of incident power; their sum may reach unity for
    a lossless article but not exceed it. Representation error at the lossless
    edge is absorbed, the engineering limit is not widened.
    """
    reflection = _magnitude(reflection_magnitude, "reflection_magnitude")
    transmission = _magnitude(transmission_magnitude, "transmission_magnitude")
    total = reflection * reflection + transmission * transmission
    passive = total <= UNIT_MAGNITUDE or math.isclose(
        total, UNIT_MAGNITUDE, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )
    findings = []
    if not passive:
        findings.append(
            "power fractions sum to %.9f, above unity: check the calibration "
            "and the port assignment" % total
        )
    return {
        "power_sum": total,
        "dissipated_fraction": max(0.0, UNIT_MAGNITUDE - total),
        "passive": passive,
        "compliant": passive,
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# Reference comparison and absolute limits
# ----------------------------------------------------------------------------

def compare_to_reference(measured_db, reference_db, tolerance_db, quantity="quantity"):
    """Compare a measured decibel value against the component-level reference."""
    for name, value in (("measured_db", measured_db), ("reference_db", reference_db)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a number, got %r" % (name, value))
    if not isinstance(tolerance_db, (int, float)) or isinstance(tolerance_db, bool):
        raise ValueError("tolerance_db must be a number, got %r" % (tolerance_db,))
    tolerance = float(tolerance_db)
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError(
            "tolerance_db must be finite and strictly positive, got %r" % (tolerance_db,)
        )
    measured = float(measured_db)
    reference = float(reference_db)
    if math.isinf(measured) and math.isinf(reference) and measured == reference:
        deviation = 0.0
    elif math.isinf(measured) or math.isinf(reference):
        deviation = math.inf if measured > reference else -math.inf
    else:
        deviation = measured - reference
    magnitude = abs(deviation)
    within = magnitude <= tolerance or math.isclose(
        magnitude, tolerance, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )
    findings = []
    if not within:
        findings.append(
            "%s deviates %+.4f dB from the reference sweep, outside the %.4f dB "
            "tolerance" % (quantity, deviation, tolerance)
        )
    return {
        "quantity": quantity,
        "deviation_db": deviation,
        "tolerance_db": tolerance,
        "within_tolerance": within,
        "compliant": within,
        "findings": findings,
    }


def check_absolute_limits(measured_return_loss_db, measured_insertion_loss_db, limits):
    """Screen a point against the minimum return-loss and maximum insertion-loss."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    for key in ("min_return_loss_db", "max_insertion_loss_db"):
        if key not in limits:
            raise ValueError("limits missing %r" % key)
        value = limits[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("limits[%r] must be a number, got %r" % (key, value))
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("limits[%r] must be finite and strictly positive" % key)
    min_rl = float(limits["min_return_loss_db"])
    max_il = float(limits["max_insertion_loss_db"])

    findings = []
    rl_ok = measured_return_loss_db >= min_rl or math.isclose(
        measured_return_loss_db, min_rl, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )
    if not rl_ok:
        findings.append(
            "return-loss %.4f dB below the minimum %.4f dB"
            % (measured_return_loss_db, min_rl)
        )
    il_ok = measured_insertion_loss_db <= max_il or math.isclose(
        measured_insertion_loss_db, max_il, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )
    if not il_ok:
        findings.append(
            "insertion-loss %.4f dB above the maximum %.4f dB"
            % (measured_insertion_loss_db, max_il)
        )
    return {
        "return_loss_ok": rl_ok,
        "insertion_loss_ok": il_ok,
        "compliant": not findings,
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# Per-point and whole-sweep evaluation
# ----------------------------------------------------------------------------

def evaluate_sweep_point(point, tolerance_db, limits):
    """Screen one measured frequency point against reference and limits."""
    if not isinstance(point, dict):
        raise ValueError("sweep point must be a mapping, got %r" % (point,))
    for key in (
        "frequency_hz",
        "reflection_magnitude",
        "transmission_magnitude",
        "reference_return_loss_db",
        "reference_insertion_loss_db",
    ):
        if key not in point:
            raise ValueError("sweep point missing %r" % key)

    frequency = point["frequency_hz"]
    if not isinstance(frequency, (int, float)) or isinstance(frequency, bool):
        raise ValueError("frequency_hz must be a number, got %r" % (frequency,))
    frequency = float(frequency)
    if not math.isfinite(frequency) or frequency <= 0.0:
        raise ValueError("frequency_hz must be finite and strictly positive")

    passivity = check_passivity(
        point["reflection_magnitude"], point["transmission_magnitude"]
    )
    measured_rl = return_loss_db(point["reflection_magnitude"])
    measured_il = insertion_loss_db(point["transmission_magnitude"])
    vswr = vswr_from_reflection(point["reflection_magnitude"])

    rl_cmp = compare_to_reference(
        measured_rl, point["reference_return_loss_db"], tolerance_db, "return-loss"
    )
    il_cmp = compare_to_reference(
        measured_il, point["reference_insertion_loss_db"], tolerance_db, "insertion-loss"
    )
    absolute = check_absolute_limits(measured_rl, measured_il, limits)

    findings = []
    for block in (passivity, rl_cmp, il_cmp, absolute):
        for item in block["findings"]:
            findings.append("%.6g Hz: %s" % (frequency, item))

    return {
        "frequency_hz": frequency,
        "return_loss_db": measured_rl,
        "insertion_loss_db": measured_il,
        "vswr": vswr,
        "passivity": passivity,
        "return_loss_comparison": rl_cmp,
        "insertion_loss_comparison": il_cmp,
        "absolute_limits": absolute,
        "compliant": not findings,
        "findings": findings,
    }


_REQUIRED_KEYS = (
    "sweep",
    "band_low_hz",
    "band_high_hz",
    "min_points",
    "tolerance_db",
    "limits",
)


def evaluate_pre_run_sweep(record):
    """Run the clause 8.4 pre-run gate over one installed-article sweep."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    missing = [key for key in _REQUIRED_KEYS if key not in record]
    if missing:
        raise ValueError("sweep record missing keys: %s" % ", ".join(sorted(missing)))
    sweep = record["sweep"]
    if not isinstance(sweep, (list, tuple)) or not sweep:
        raise ValueError("sweep must be a non-empty list of measured points")

    grid = validate_frequency_grid(
        [p.get("frequency_hz") if isinstance(p, dict) else p for p in sweep],
        record["band_low_hz"],
        record["band_high_hz"],
        record["min_points"],
    )
    points = [
        evaluate_sweep_point(point, record["tolerance_db"], record["limits"])
        for point in sweep
    ]

    findings = list(grid["findings"])
    for result in points:
        findings.extend(result["findings"])

    failing = [p for p in points if not p["compliant"]]
    worst = None
    if failing:
        worst = min(failing, key=lambda p: p["return_loss_db"])

    return {
        "grid": grid,
        "points": points,
        "failing_points": len(failing),
        "worst_point_hz": None if worst is None else worst["frequency_hz"],
        "compliant": not findings,
        "findings": findings,
        "verdict": "CLEARED-TO-RUN" if not findings else "HOLD-BEFORE-RUN",
    }
