#!/usr/bin/env python3
"""Definition of the cut-off point of a coverglass reflectance coating.

Anchor: ECSS-E-ST-20-08C clause 8.7.5.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The cut-off is a definition before it is a number, and the definition is
what the whole measurement hangs on:

    cut-off  the LONG-wavelength point at which the falling edge of the
             reflectance curve reaches HALF of the ABSOLUTE measured
             reflectance of the band

Three words in that sentence do the work. LONG-wavelength separates the
cut-off from the cut-on, which is the same half level found on the
rising side. ABSOLUTE ties the half level to what the instrument
actually read, not to a nominal 100 percent, not to a reference sample,
and not to a percentage of a normalised curve. HALF fixes the fraction,
so a coating whose band peaks at 80 percent has its edges at 40 percent
and one peaking at 50 percent has them at 25.

Normalising first is the failure this definition is written against. A
trace scaled to a reference before the half level is taken reports an
edge that moves with the reference, so two labs measuring one coverglass
publish two cut-offs and neither is wrong on its own terms.

The band edge rarely lands on a scanned wavelength, so the crossing is
interpolated linearly between the two points that straddle the half
level. A scan that stops before the falling edge reaches that level has
not measured a cut-off; it has measured that the cut-off is somewhere
past the end of the scan, which is a different statement.

The peak floor and the scan-point floor below are a declared policy, not
a physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# The only basis this clause's definition recognises.
ABSOLUTE_HALF_LEVEL_BASIS = "absolute-measured-reflectance"
RECOGNISED_HALF_LEVEL_BASES = (
    ABSOLUTE_HALF_LEVEL_BASIS,
    "normalised-to-reference-reflectance",
    "fixed-nominal-percent",
)

HALF_LEVEL_BASIS_MISAPPLIED = "half-level-basis-misapplied"
REFLECTANCE_BAND_TOO_WEAK = "reflectance-band-too-weak-for-a-half-level"
CUT_OFF_BEYOND_SCAN_RANGE = "cut-off-beyond-the-scanned-range"
CUT_OFF_DETERMINED = "cut-off-determined"

DEFAULT_CUT_OFF_POLICY = {
    "min_usable_peak_percent": 20.0,
    "min_scan_points": 5,
    "max_reflectance_percent": 100.0,
    "half_level_fraction": 0.5,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def validate_cut_off_policy(policy):
    """Check a cut-off determination policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
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
    fraction = _require_positive(
        "half_level_fraction", policy.get("half_level_fraction")
    )
    if fraction >= 1.0:
        raise ValueError(
            "half_level_fraction %g must sit below the band peak it divides"
            % (fraction,)
        )
    points = policy.get("min_scan_points")
    if not isinstance(points, int) or isinstance(points, bool) or points < 3:
        raise ValueError(
            "min_scan_points must be an integer of at least 3, got %r" % (points,)
        )
    return policy


def validate_reflectance_trace(trace, policy=DEFAULT_CUT_OFF_POLICY):
    """Return the trace as ordered (wavelength_nm, reflectance_percent) pairs."""
    validate_cut_off_policy(policy)
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


def absolute_peak_reflectance(trace, policy=DEFAULT_CUT_OFF_POLICY):
    """The largest reflectance the scan actually read, with nothing scaled."""
    points = validate_reflectance_trace(trace, policy)
    return max(reflectance for _, reflectance in points)


def half_of_absolute_reflectance(trace, policy=DEFAULT_CUT_OFF_POLICY):
    """The level the definition puts the cut-off at: half the absolute peak."""
    validate_cut_off_policy(policy)
    peak = absolute_peak_reflectance(trace, policy)
    return peak * float(policy["half_level_fraction"])


def half_level_from_reference(reference_percent, policy=DEFAULT_CUT_OFF_POLICY):
    """The level a normalised basis would use -- shown so it can be refused."""
    validate_cut_off_policy(policy)
    reference = _require_positive("reference_percent", reference_percent)
    return reference * float(policy["half_level_fraction"])


def band_is_strong_enough(trace, policy=DEFAULT_CUT_OFF_POLICY):
    """True when the band peaks high enough for a half level to describe it."""
    validate_cut_off_policy(policy)
    peak = absolute_peak_reflectance(trace, policy)
    return _at_least(peak, float(policy["min_usable_peak_percent"]))


def _peak_index(points):
    peak = max(reflectance for _, reflectance in points)
    for index, (_, reflectance) in enumerate(points):
        if reflectance == peak:
            return index
    raise ValueError("trace has no peak")  # pragma: no cover - unreachable


def _last_peak_index(points):
    peak = max(reflectance for _, reflectance in points)
    last = 0
    for index, (_, reflectance) in enumerate(points):
        if reflectance == peak:
            last = index
    return last


def cut_off_is_resolvable(trace, policy=DEFAULT_CUT_OFF_POLICY):
    """True when the falling edge reaches the half level inside the scan."""
    points = validate_reflectance_trace(trace, policy)
    level = half_of_absolute_reflectance(points, policy)
    top = _last_peak_index(points)
    for index in range(top, len(points) - 1):
        upper = points[index][1]
        lower = points[index + 1][1]
        if _at_least(upper, level) and _at_most(lower, level) and upper > lower:
            return True
    return False


def cut_off_wavelength(trace, policy=DEFAULT_CUT_OFF_POLICY):
    """The long-wavelength half-of-absolute-reflectance point: the cut-off."""
    points = validate_reflectance_trace(trace, policy)
    level = half_of_absolute_reflectance(points, policy)
    top = _last_peak_index(points)
    for index in range(top, len(points) - 1):
        w_high, r_high = points[index]
        w_low, r_low = points[index + 1]
        if _at_least(r_high, level) and _at_most(r_low, level) and r_high > r_low:
            return w_high + (r_high - level) * (w_low - w_high) / (r_high - r_low)
    raise ValueError(
        "the falling edge never reaches the %g percent half level inside the "
        "scanned range" % (level,)
    )


def cut_on_wavelength(trace, policy=DEFAULT_CUT_OFF_POLICY):
    """The rising-edge partner of the cut-off, at the same half level."""
    points = validate_reflectance_trace(trace, policy)
    level = half_of_absolute_reflectance(points, policy)
    top = _peak_index(points)
    for index in range(top):
        w_low, r_low = points[index]
        w_high, r_high = points[index + 1]
        if _at_most(r_low, level) and _at_least(r_high, level) and r_high > r_low:
            return w_low + (level - r_low) * (w_high - w_low) / (r_high - r_low)
    raise ValueError(
        "the rising edge never reaches the %g percent half level inside the "
        "scanned range" % (level,)
    )


def band_width_nm(trace, policy=DEFAULT_CUT_OFF_POLICY):
    """How wide the high reflectance band is between its two half-level edges."""
    return cut_off_wavelength(trace, policy) - cut_on_wavelength(trace, policy)


def scan_upper_limit_nm(trace, policy=DEFAULT_CUT_OFF_POLICY):
    """The longest wavelength the scan reached."""
    points = validate_reflectance_trace(trace, policy)
    return points[-1][0]


def determine_cut_off(case, policy=DEFAULT_CUT_OFF_POLICY):
    """Full clause 8.7.5.3.1 determination for one measured reflectance band."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_cut_off_policy(policy)
    if "trace" not in case:
        raise ValueError(
            "case is missing a trace key; an absent scan is not an empty one"
        )

    basis = case.get("half_level_basis", ABSOLUTE_HALF_LEVEL_BASIS)
    if basis not in RECOGNISED_HALF_LEVEL_BASES:
        raise ValueError(
            "unknown half_level_basis %r; recognised bases are %s"
            % (basis, ", ".join(RECOGNISED_HALF_LEVEL_BASES))
        )

    points = validate_reflectance_trace(case["trace"], policy)
    peak = max(reflectance for _, reflectance in points)
    level = peak * float(policy["half_level_fraction"])

    findings = []
    result = {
        "half_level_basis": basis,
        "absolute_peak_percent": peak,
        "half_level_percent": level,
        "scan_upper_limit_nm": points[-1][0],
        "cut_off_nm": None,
        "cut_on_nm": None,
        "band_width_nm": None,
        "findings": findings,
    }

    if basis != ABSOLUTE_HALF_LEVEL_BASIS:
        findings.append(
            "the half level was taken on a %s basis; this clause defines the "
            "cut-off at half of the absolute measured reflectance" % (basis,)
        )
        result["verdict"] = HALF_LEVEL_BASIS_MISAPPLIED
        return result

    if not band_is_strong_enough(points, policy):
        findings.append(
            "the absolute peak of %.3f percent is below the %.3f percent a half "
            "level needs before it describes a reflectance band"
            % (peak, float(policy["min_usable_peak_percent"]))
        )
        result["verdict"] = REFLECTANCE_BAND_TOO_WEAK
        return result

    if not cut_off_is_resolvable(points, policy):
        findings.append(
            "the falling edge is still above the %.3f percent half level at "
            "%.3f nm, so the cut-off lies past the end of the scan rather than "
            "inside it" % (level, points[-1][0])
        )
        result["verdict"] = CUT_OFF_BEYOND_SCAN_RANGE
        return result

    cut_off = cut_off_wavelength(points, policy)
    result["cut_off_nm"] = cut_off
    try:
        cut_on = cut_on_wavelength(points, policy)
    except ValueError:
        cut_on = None
        findings.append(
            "the rising edge is not inside the scan, so the band width is not "
            "available even though the cut-off is"
        )
    if cut_on is not None:
        result["cut_on_nm"] = cut_on
        result["band_width_nm"] = cut_off - cut_on

    result["verdict"] = CUT_OFF_DETERMINED
    return result
