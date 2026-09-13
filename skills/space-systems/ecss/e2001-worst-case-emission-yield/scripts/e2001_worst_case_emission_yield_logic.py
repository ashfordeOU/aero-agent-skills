#!/usr/bin/env python3
"""Worst-case emission-yield envelope (ECSS-E-ST-20-01C clause 9.3).

Deterministic, offline, stdlib-only logic that builds the worst-case
secondary-electron-emission-yield curve from a set of measured
yield-versus-primary-electron-energy curves: at every primary-electron-energy
the envelope takes the highest yield any measured curve shows there.

Paraphrased procedure only; the standard and clause are cited as the anchor.
"""

import math

UNITY_YIELD = 1.0
MIN_POINTS_PER_CURVE = 3
ENERGY_MERGE_TOL_EV = 1e-9
REL_TOL = 1e-9
ABS_TOL = 1e-12

SUSTAINED_GROWTH = "supports-sustained-emission-growth"
NO_SUSTAINED_GROWTH = "no-sustained-emission-growth"


def _close(a, b):
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def within_limit(value, limit):
    """True when value <= limit, absorbing float representation error."""
    return value < limit or _close(value, limit)


def meets_or_exceeds(value, limit):
    """True when value >= limit, absorbing float representation error."""
    return value > limit or _close(value, limit)


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


# --- Curve handling --------------------------------------------------------
def validate_curve(curve):
    """Validate one measured yield curve and return a normalised copy."""
    if not isinstance(curve, dict):
        raise ValueError("curve must be a mapping with 'curve_id' and 'points'")
    curve_id = curve.get("curve_id")
    if not isinstance(curve_id, str) or not curve_id.strip():
        raise ValueError("curve_id must be a non-empty string")
    raw_points = curve.get("points")
    if not isinstance(raw_points, (list, tuple)):
        raise ValueError("curve %r: points must be a list of (energy_ev, yield) pairs"
                         % curve_id)
    if len(raw_points) < MIN_POINTS_PER_CURVE:
        raise ValueError("curve %r: needs at least %d measured points, got %d"
                         % (curve_id, MIN_POINTS_PER_CURVE, len(raw_points)))
    points = []
    previous_energy = None
    for index, pair in enumerate(raw_points):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("curve %r: point %d must be an (energy_ev, yield) pair"
                             % (curve_id, index))
        energy = _require_number(pair[0], "curve %r point %d energy" % (curve_id, index))
        yield_value = _require_number(pair[1], "curve %r point %d yield"
                                      % (curve_id, index))
        if energy <= 0.0:
            raise ValueError("curve %r: primary-electron-energy must be positive at "
                             "point %d, got %r" % (curve_id, index, energy))
        if yield_value < 0.0:
            raise ValueError("curve %r: yield must not be negative at point %d, got %r"
                             % (curve_id, index, yield_value))
        if previous_energy is not None and energy <= previous_energy:
            raise ValueError("curve %r: energies must strictly increase; %r follows %r"
                             % (curve_id, energy, previous_energy))
        previous_energy = energy
        points.append((energy, yield_value))
    return {"curve_id": curve_id.strip(), "points": points}


def curve_energy_span(curve):
    """Return (lowest, highest) measured primary-electron-energy of a curve."""
    points = validate_curve(curve)["points"]
    return points[0][0], points[-1][0]


def interpolate_yield(curve, energy):
    """Linearly interpolate a curve at one energy; extrapolation is refused."""
    points = validate_curve(curve)["points"]
    target = _require_number(energy, "energy")
    low, high = points[0][0], points[-1][0]
    if target < low and not _close(target, low):
        raise ValueError("energy %r is below the measured span (%r eV); "
                         "extrapolation is not permitted" % (target, low))
    if target > high and not _close(target, high):
        raise ValueError("energy %r is above the measured span (%r eV); "
                         "extrapolation is not permitted" % (target, high))
    for index in range(len(points) - 1):
        left_e, left_y = points[index]
        right_e, right_y = points[index + 1]
        if target < left_e and not _close(target, left_e):
            continue
        if target > right_e and not _close(target, right_e):
            continue
        if _close(target, left_e):
            return left_y
        if _close(target, right_e):
            return right_y
        fraction = (target - left_e) / (right_e - left_e)
        return left_y + fraction * (right_y - left_y)
    return points[-1][1]


# --- Common grid -----------------------------------------------------------
def common_energy_span(curves):
    """Energy interval covered by every curve in the set."""
    if not isinstance(curves, (list, tuple)) or not curves:
        raise ValueError("at least one measured curve is required")
    spans = [curve_energy_span(curve) for curve in curves]
    low = max(span[0] for span in spans)
    high = min(span[1] for span in spans)
    if high < low or _close(high, low):
        raise ValueError("measured curves share no usable energy interval "
                         "(overlap %r-%r eV)" % (low, high))
    return low, high


def common_energy_grid(curves):
    """Shared energy grid: every measured energy inside the common overlap."""
    low, high = common_energy_span(curves)
    energies = [low, high]
    for curve in curves:
        for energy, _yield in validate_curve(curve)["points"]:
            if energy < low or energy > high:
                continue
            energies.append(energy)
    energies.sort()
    grid = []
    for energy in energies:
        if grid and abs(energy - grid[-1]) <= ENERGY_MERGE_TOL_EV:
            continue
        grid.append(energy)
    if len(grid) < 2:
        raise ValueError("shared energy grid collapsed to fewer than two points")
    return grid


# --- Envelope --------------------------------------------------------------
def worst_case_envelope(curves, grid=None):
    """Highest yield across the curve set at each shared-grid energy."""
    validated = [validate_curve(curve) for curve in curves]
    if grid is None:
        grid = common_energy_grid(validated)
    else:
        if not isinstance(grid, (list, tuple)) or len(grid) < 2:
            raise ValueError("grid must hold at least two energies")
        grid = [_require_number(e, "grid energy") for e in grid]
        low, high = common_energy_span(validated)
        for energy in grid:
            if not meets_or_exceeds(energy, low) or not within_limit(energy, high):
                raise ValueError("grid energy %r lies outside the common overlap "
                                 "%r-%r eV" % (energy, low, high))
    envelope = []
    for energy in grid:
        best_yield = None
        best_curve = None
        for curve in validated:
            value = interpolate_yield(curve, energy)
            if best_yield is None or value > best_yield:
                best_yield = value
                best_curve = curve["curve_id"]
        envelope.append({"energy_ev": energy, "yield": best_yield,
                         "curve_id": best_curve})
    return envelope


def envelope_peak(envelope):
    """Peak of the envelope; the lowest energy wins an exact tie."""
    if not isinstance(envelope, (list, tuple)) or not envelope:
        raise ValueError("envelope must hold at least one point")
    best = envelope[0]
    for point in envelope[1:]:
        if point["yield"] > best["yield"]:
            best = point
    return dict(best)


def yield_at_energy(envelope, energy):
    """Interpolate the envelope itself at one energy."""
    if not isinstance(envelope, (list, tuple)) or len(envelope) < 2:
        raise ValueError("envelope must hold at least two points")
    curve = {"curve_id": "envelope",
             "points": [(p["energy_ev"], p["yield"]) for p in envelope]}
    if len(curve["points"]) < MIN_POINTS_PER_CURVE:
        curve["points"] = curve["points"] + [(curve["points"][-1][0] * 2.0,
                                              curve["points"][-1][1])]
    return interpolate_yield(curve, energy)


def crossover_energies(envelope, threshold=UNITY_YIELD):
    """First and second energies at which the envelope passes the threshold."""
    if not isinstance(envelope, (list, tuple)) or len(envelope) < 2:
        raise ValueError("envelope must hold at least two points")
    level = _require_number(threshold, "threshold")
    if level <= 0.0:
        raise ValueError("threshold must be positive, got %r" % (level,))
    crossings = []
    for index in range(len(envelope)):
        energy = envelope[index]["energy_ev"]
        value = envelope[index]["yield"]
        if _close(value, level):
            if not crossings or not _close(crossings[-1], energy):
                crossings.append(energy)
            continue
        if index == 0:
            continue
        previous_e = envelope[index - 1]["energy_ev"]
        previous_y = envelope[index - 1]["yield"]
        if _close(previous_y, level):
            continue
        if (previous_y - level) * (value - level) < 0.0:
            fraction = (level - previous_y) / (value - previous_y)
            crossings.append(previous_e + fraction * (energy - previous_e))
    first = crossings[0] if crossings else None
    second = crossings[1] if len(crossings) > 1 else None
    return {"first_crossover_ev": first, "second_crossover_ev": second,
            "all_crossings_ev": crossings}


def assess_susceptibility(envelope, allowable_peak_yield=None):
    """State whether the envelope supports sustained emission growth."""
    peak = envelope_peak(envelope)
    crossings = crossover_energies(envelope)
    grows = meets_or_exceeds(peak["yield"], UNITY_YIELD)
    findings = []
    verdict = SUSTAINED_GROWTH if grows else NO_SUSTAINED_GROWTH
    if grows and crossings["first_crossover_ev"] is None:
        findings.append("envelope stays at or above unity across the whole shared "
                        "grid; the first crossover lies below the measured span")
    if grows and crossings["second_crossover_ev"] is None:
        findings.append("envelope has not fallen back through unity inside the "
                        "measured span")
    if allowable_peak_yield is not None:
        allowable = _require_number(allowable_peak_yield, "allowable_peak_yield")
        if allowable <= 0.0:
            raise ValueError("allowable_peak_yield must be positive")
        if not within_limit(peak["yield"], allowable):
            findings.append("envelope peak %.4g exceeds the allowable %.4g"
                            % (peak["yield"], allowable))
    return {"verdict": verdict, "peak": peak, "crossovers": crossings,
            "findings": findings, "compliant": not findings}


def check_assessment_coverage(curves, required_span_ev):
    """Confirm the shared overlap covers the energy range the analysis reads."""
    span = tuple(required_span_ev)
    if len(span) != 2:
        raise ValueError("required_span_ev must hold two energies")
    need_low = _require_number(span[0], "required_span_ev[0]")
    need_high = _require_number(span[1], "required_span_ev[1]")
    if need_low <= 0.0 or not need_high > need_low:
        raise ValueError("required_span_ev must be positive and increasing")
    low, high = common_energy_span(curves)
    covered = within_limit(low, need_low) and meets_or_exceeds(high, need_high)
    return {"covered": covered, "overlap_ev": (low, high),
            "required_ev": (need_low, need_high)}


def summarize_envelope(envelope, allowable_peak_yield=None):
    """Render the envelope verdict as reviewable text lines."""
    assessment = assess_susceptibility(envelope, allowable_peak_yield)
    peak = assessment["peak"]
    crossings = assessment["crossovers"]
    lines = ["ECSS-E-ST-20-01C clause 9.3 worst-case emission-yield envelope",
             "grid points: %d over %.6g-%.6g eV"
             % (len(envelope), envelope[0]["energy_ev"], envelope[-1]["energy_ev"]),
             "peak yield %.4g at %.6g eV (driven by curve %s)"
             % (peak["yield"], peak["energy_ev"], peak["curve_id"]),
             "verdict: %s" % assessment["verdict"]]
    for key, label in (("first_crossover_ev", "first crossover"),
                       ("second_crossover_ev", "second crossover")):
        value = crossings[key]
        lines.append("%s: %s" % (label,
                                 "not inside the measured span" if value is None
                                 else "%.6g eV" % value))
    for finding in assessment["findings"]:
        lines.append("  finding: %s" % finding)
    return lines
