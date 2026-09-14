#!/usr/bin/env python3
"""Cut-on of a coverglass coating against the source control drawing.

Anchor: ECSS-E-ST-20-08C clause 8.7.5.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A coverglass reflectance coating is bought to a drawing, not to a
preference. The drawing carries one cut-on figure, and the requirement
is that the coating the lot actually delivers puts its short-wavelength
band edge on that figure, inside the tolerance the drawing allows.

Cut-on is taken from the measured spectrum the same way its long-
wavelength partner is: the half level is half of the ABSOLUTE measured
reflectance peak, and the cut-on is the short-wavelength point at which
the rising edge crosses that level. Normalising the trace to a nominal
100 percent reference first moves the half level and therefore moves the
reported cut-on, which is how a conforming lot gets rejected and a
drifting one gets accepted.

Four outcomes are kept apart because they need different actions:

    drawing carries no cut-on   a procurement gap; nothing to compare
    coating never measured      a data gap; nothing to compare either
    band too weak / no crossing an instrument or coating problem
    cut-on measured             the only case where a deviation means
                                what the clause says it means

An absent drawing entry is not a cut-on of zero, and an unmeasured lot
is not a lot at the nominal. Both are reported as what they are.

The tolerance default, the minimum usable peak and the scan-point floor
below are a declared policy, not a physical constant: a project
substitutes the figures its own drawing carries.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DRAWING_CUT_ON_ENTRY_MISSING = "drawing-cut-on-entry-missing"
CUT_ON_NOT_MEASURED = "cut-on-not-measured"
REFLECTANCE_BAND_TOO_WEAK = "reflectance-band-too-weak-for-a-half-level"
CUT_ON_NOT_RESOLVED = "cut-on-not-resolved-within-scan"
HALF_LEVEL_BASIS_MISAPPLIED = "half-level-basis-misapplied"
CUT_ON_OUTSIDE_DRAWING_TOLERANCE = "cut-on-outside-drawing-tolerance"
CUT_ON_MATCHES_DRAWING = "cut-on-matches-drawing"

# Only the absolute measured peak gives the half level this clause means.
ABSOLUTE_HALF_LEVEL_BASIS = "absolute-measured-reflectance"
RECOGNISED_HALF_LEVEL_BASES = (
    ABSOLUTE_HALF_LEVEL_BASIS,
    "normalised-to-reference-reflectance",
    "peak-normalised-percent",
)

DEFAULT_CUT_ON_POLICY = {
    "default_tolerance_nm": 10.0,
    "min_usable_peak_percent": 20.0,
    "min_scan_points": 5,
    "max_reflectance_percent": 100.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

_MIN_WAVELENGTH_NM = 0.0


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_cut_on_policy(policy):
    """Check a cut-on acceptance policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("default_tolerance_nm", policy.get("default_tolerance_nm"))
    ceiling = _require_positive(
        "max_reflectance_percent", policy.get("max_reflectance_percent")
    )
    peak_floor = _require_positive(
        "min_usable_peak_percent", policy.get("min_usable_peak_percent")
    )
    if peak_floor > ceiling:
        raise ValueError(
            "min_usable_peak_percent %g cannot exceed max_reflectance_percent %g"
            % (peak_floor, ceiling)
        )
    points = policy.get("min_scan_points")
    if not isinstance(points, int) or isinstance(points, bool) or points < 3:
        raise ValueError(
            "min_scan_points must be an integer of at least 3, got %r" % (points,)
        )
    return policy


def validate_reflectance_trace(trace, policy=DEFAULT_CUT_ON_POLICY):
    """Return the trace as ordered (wavelength_nm, reflectance_percent) pairs."""
    validate_cut_on_policy(policy)
    if not isinstance(trace, (list, tuple)):
        raise ValueError("trace must be a sequence of wavelength/reflectance pairs")
    ceiling = float(policy["max_reflectance_percent"])
    points = []
    for entry in trace:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError(
                "each trace point must be a (wavelength_nm, reflectance_percent) "
                "pair, got %r" % (entry,)
            )
        wavelength = _require_positive("wavelength_nm", entry[0])
        reflectance = _require_non_negative("reflectance_percent", entry[1])
        if wavelength <= _MIN_WAVELENGTH_NM:
            raise ValueError("wavelength_nm must be above zero, got %r" % (entry[0],))
        if reflectance > ceiling and not math.isclose(
            reflectance, ceiling, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            raise ValueError(
                "reflectance_percent %g exceeds the %g percent ceiling"
                % (reflectance, ceiling)
            )
        points.append((wavelength, reflectance))
    if len(points) < int(policy["min_scan_points"]):
        raise ValueError(
            "trace has %d points, the policy asks for at least %d"
            % (len(points), int(policy["min_scan_points"]))
        )
    for earlier, later in zip(points, points[1:]):
        if not later[0] > earlier[0]:
            raise ValueError(
                "trace wavelengths must increase; %g follows %g"
                % (later[0], earlier[0])
            )
    return tuple(points)


def absolute_peak_reflectance(trace, policy=DEFAULT_CUT_ON_POLICY):
    """The largest reflectance the scan actually measured, un-normalised."""
    points = validate_reflectance_trace(trace, policy)
    return max(reflectance for _, reflectance in points)


def half_of_absolute_reflectance(trace, policy=DEFAULT_CUT_ON_POLICY):
    """The level the clause takes the band edges at: half the measured peak."""
    return absolute_peak_reflectance(trace, policy) / 2.0


def band_is_strong_enough(trace, policy=DEFAULT_CUT_ON_POLICY):
    """True when the peak is high enough for a half level to mean anything."""
    validate_cut_on_policy(policy)
    peak = absolute_peak_reflectance(trace, policy)
    return _at_least(peak, float(policy["min_usable_peak_percent"]))


def _peak_index(points):
    peak = max(reflectance for _, reflectance in points)
    for index, (_, reflectance) in enumerate(points):
        if reflectance == peak:
            return index
    raise ValueError("trace has no peak")  # pragma: no cover - unreachable


def cut_on_is_resolvable(trace, policy=DEFAULT_CUT_ON_POLICY):
    """True when the rising edge crosses the half level inside the scan."""
    points = validate_reflectance_trace(trace, policy)
    half = max(reflectance for _, reflectance in points) / 2.0
    top = _peak_index(points)
    for index in range(top):
        lower = points[index][1]
        upper = points[index + 1][1]
        if _at_most(lower, half) and _at_least(upper, half) and upper > lower:
            return True
    return False


def cut_on_wavelength(trace, policy=DEFAULT_CUT_ON_POLICY):
    """Short-wavelength point where the rising edge reaches the half level."""
    points = validate_reflectance_trace(trace, policy)
    half = max(reflectance for _, reflectance in points) / 2.0
    top = _peak_index(points)
    for index in range(top):
        w_low, r_low = points[index]
        w_high, r_high = points[index + 1]
        if _at_most(r_low, half) and _at_least(r_high, half) and r_high > r_low:
            return w_low + (half - r_low) * (w_high - w_low) / (r_high - r_low)
    raise ValueError(
        "the rising edge never crosses the %g percent half level inside the scan"
        % (half,)
    )


def drawing_cut_on(drawing, policy=DEFAULT_CUT_ON_POLICY):
    """Read the cut-on figure and its tolerance out of the drawing block."""
    validate_cut_on_policy(policy)
    if not isinstance(drawing, dict):
        raise ValueError("drawing must be a mapping, got %r" % (drawing,))
    if "cut_on_nm" not in drawing:
        raise ValueError(
            "drawing carries no cut_on_nm entry; an absent figure is not a "
            "cut-on of zero"
        )
    nominal = _require_positive("drawing cut_on_nm", drawing["cut_on_nm"])
    tolerance = drawing.get("tolerance_nm", policy["default_tolerance_nm"])
    tolerance = _require_positive("drawing tolerance_nm", tolerance)
    return nominal, tolerance


def cut_on_deviation_nm(measured_nm, drawing_nm):
    """Signed distance of the measured cut-on from the drawing figure."""
    measured = _require_positive("measured_nm", measured_nm)
    nominal = _require_positive("drawing_nm", drawing_nm)
    return measured - nominal


def cut_on_matches_drawing(measured_nm, drawing_nm, tolerance_nm):
    """True when the deviation sits inside the tolerance the drawing allows."""
    tolerance = _require_positive("tolerance_nm", tolerance_nm)
    deviation = cut_on_deviation_nm(measured_nm, drawing_nm)
    return _at_most(abs(deviation), tolerance)


def tolerance_band_nm(drawing_nm, tolerance_nm):
    """The acceptance window the drawing figure and its tolerance describe."""
    nominal = _require_positive("drawing_nm", drawing_nm)
    tolerance = _require_positive("tolerance_nm", tolerance_nm)
    return (nominal - tolerance, nominal + tolerance)


def assess_cut_on_requirement(case, policy=DEFAULT_CUT_ON_POLICY):
    """Full clause 8.7.5.2.3 judgement for one coverglass coating lot."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_cut_on_policy(policy)
    if "drawing" not in case:
        raise ValueError(
            "case is missing a drawing key; an absent drawing block is not the "
            "same as a drawing with no cut-on entry"
        )

    findings = []
    result = {
        "drawing_cut_on_nm": None,
        "tolerance_nm": None,
        "tolerance_band_nm": None,
        "measured_cut_on_nm": None,
        "absolute_peak_percent": None,
        "half_level_percent": None,
        "deviation_nm": None,
        "half_level_basis": None,
        "findings": findings,
    }

    drawing = case["drawing"]
    if drawing is None or (isinstance(drawing, dict) and "cut_on_nm" not in drawing):
        findings.append(
            "the source control drawing carries no cut-on figure, so there is "
            "nothing for the coating to match"
        )
        result["verdict"] = DRAWING_CUT_ON_ENTRY_MISSING
        return result

    nominal, tolerance = drawing_cut_on(drawing, policy)
    result["drawing_cut_on_nm"] = nominal
    result["tolerance_nm"] = tolerance
    result["tolerance_band_nm"] = tolerance_band_nm(nominal, tolerance)

    measurement = case.get("measurement")
    if measurement is None:
        findings.append(
            "no reflectance measurement is presented for the lot; an unmeasured "
            "coating is not a coating at the nominal"
        )
        result["verdict"] = CUT_ON_NOT_MEASURED
        return result
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))

    basis = measurement.get("half_level_basis", ABSOLUTE_HALF_LEVEL_BASIS)
    if basis not in RECOGNISED_HALF_LEVEL_BASES:
        raise ValueError(
            "unknown half_level_basis %r; recognised bases are %s"
            % (basis, ", ".join(RECOGNISED_HALF_LEVEL_BASES))
        )
    result["half_level_basis"] = basis

    trace = measurement.get("trace")
    if trace is None:
        findings.append(
            "the measurement block carries no reflectance trace, so no cut-on "
            "can be taken from it"
        )
        result["verdict"] = CUT_ON_NOT_MEASURED
        return result

    points = validate_reflectance_trace(trace, policy)
    peak = max(reflectance for _, reflectance in points)
    result["absolute_peak_percent"] = peak
    result["half_level_percent"] = peak / 2.0

    if not band_is_strong_enough(points, policy):
        findings.append(
            "the absolute peak of %.3f percent is below the %.3f percent a half "
            "level needs to describe a reflectance band"
            % (peak, float(policy["min_usable_peak_percent"]))
        )
        result["verdict"] = REFLECTANCE_BAND_TOO_WEAK
        return result

    if basis != ABSOLUTE_HALF_LEVEL_BASIS:
        findings.append(
            "the half level was taken on a %s basis; the cut-on this clause "
            "asks for sits at half of the absolute measured reflectance" % (basis,)
        )
        result["verdict"] = HALF_LEVEL_BASIS_MISAPPLIED
        return result

    if not cut_on_is_resolvable(points, policy):
        findings.append(
            "the rising edge never crosses the %.3f percent half level inside "
            "the scanned range, so the cut-on falls outside the measurement"
            % (peak / 2.0,)
        )
        result["verdict"] = CUT_ON_NOT_RESOLVED
        return result

    measured = cut_on_wavelength(points, policy)
    deviation = cut_on_deviation_nm(measured, nominal)
    result["measured_cut_on_nm"] = measured
    result["deviation_nm"] = deviation

    if not cut_on_matches_drawing(measured, nominal, tolerance):
        findings.append(
            "the cut-on measured at %.3f nm sits %.3f nm from the %.3f nm the "
            "drawing calls out, beyond its %.3f nm tolerance"
            % (measured, deviation, nominal, tolerance)
        )
        result["verdict"] = CUT_ON_OUTSIDE_DRAWING_TOLERANCE
        return result

    result["verdict"] = CUT_ON_MATCHES_DRAWING
    return result
