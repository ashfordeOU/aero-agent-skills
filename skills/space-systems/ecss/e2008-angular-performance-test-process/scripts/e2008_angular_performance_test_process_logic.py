#!/usr/bin/env python3
"""Process for the angular performance measurement on a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.19.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The measurement is a sweep: the assembly output is read at a series of
sun incidence angles rather than at one. The clause's substance is the
spacing of that series, and the spacing is not uniform. Up to sixty
degrees a coarse step is enough; past sixty the sweep takes further
steps, because that is where the curve stops behaving like the cosine
the coarse region rides on.

Why the break sits there is arithmetic, not convention. Between two
measured angles the curve is read by straight-line interpolation, and
the error that leaves is bounded by

    h^2 / 8 * max |second derivative|

with h the step in radians. For a cosine the second derivative is the
cosine itself, so the bound falls as the angle opens -- yet the real
curve departs from the cosine fastest exactly there, as the coverglass
reflection climbs and the illuminated area shortens. A step chosen for
the well-behaved region is therefore the wrong step for the region the
test was run to see.

What this module decides, for a planned or an as-run sweep:

    schedule        the angles the policy asks for, coarse to the
                    breakpoint and refined beyond it
    gaps            the largest spacing each region actually leaves
    error bound     what a gap admits between two measured points
    reach           whether the sweep ever gets to the declared
                    maximum angle

The breakpoint, the two steps, the ceiling and the error allowance
below are a declared policy, not a physical constant: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ANGULAR_SWEEP_NOT_PLANNED = "angular-sweep-not-planned"
ANGULAR_SWEEP_TRUNCATED = "angular-sweep-truncated"
ANGULAR_SWEEP_UNDERSAMPLED = "angular-sweep-undersampled"
ANGULAR_SWEEP_ACCEPTED = "angular-sweep-accepted"

COARSE_REGION = "coarse-region-to-the-breakpoint"
REFINED_REGION = "refined-region-beyond-the-breakpoint"

DEFAULT_SWEEP_POLICY = {
    "step_breakpoint_deg": 60.0,
    "coarse_step_deg": 10.0,
    "refined_step_deg": 5.0,
    "max_sweep_angle_deg": 85.0,
    "angle_match_tolerance_deg": 0.5,
    "max_interpolation_error_fraction": 0.02,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

_MAX_INCIDENCE_DEG = 90.0
_ANGLE_PLACES = 9


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


def _require_incidence_angle(name, value):
    """0 degrees is normal incidence; at 90 the assembly is edge on and dark."""
    number = _require_number(name, value)
    if number < 0.0 or number >= _MAX_INCIDENCE_DEG:
        raise ValueError(
            "%s must be at least 0 and below %g degrees, got %r"
            % (name, _MAX_INCIDENCE_DEG, value)
        )
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


def _clean_angle(value):
    """Drop the float dust a repeated step accumulates in a schedule."""
    return round(value, _ANGLE_PLACES)


def validate_sweep_policy(policy):
    """Check an angular-sweep policy is complete and internally consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    breakpoint_deg = _require_incidence_angle(
        "step_breakpoint_deg", policy.get("step_breakpoint_deg")
    )
    if breakpoint_deg <= 0.0:
        raise ValueError(
            "step_breakpoint_deg %g must be above normal incidence" % (breakpoint_deg,)
        )
    coarse = _require_positive("coarse_step_deg", policy.get("coarse_step_deg"))
    refined = _require_positive("refined_step_deg", policy.get("refined_step_deg"))
    if not refined < coarse:
        raise ValueError(
            "refined_step_deg %g must be smaller than coarse_step_deg %g; the "
            "sweep takes further steps past the breakpoint, not fewer"
            % (refined, coarse)
        )
    ceiling = _require_incidence_angle(
        "max_sweep_angle_deg", policy.get("max_sweep_angle_deg")
    )
    if not ceiling > breakpoint_deg:
        raise ValueError(
            "max_sweep_angle_deg %g must be above the %g degree breakpoint"
            % (ceiling, breakpoint_deg)
        )
    _require_non_negative(
        "angle_match_tolerance_deg", policy.get("angle_match_tolerance_deg")
    )
    allowance = _require_positive(
        "max_interpolation_error_fraction",
        policy.get("max_interpolation_error_fraction"),
    )
    if allowance > 1.0:
        raise ValueError(
            "max_interpolation_error_fraction %g must not exceed 1" % (allowance,)
        )
    return policy


def step_for_angle(incidence_angle_deg, policy=DEFAULT_SWEEP_POLICY):
    """The step the sweep is allowed to take from this angle onwards."""
    validate_sweep_policy(policy)
    angle = _require_incidence_angle("incidence_angle_deg", incidence_angle_deg)
    breakpoint_deg = float(policy["step_breakpoint_deg"])
    if _at_least(angle, breakpoint_deg):
        return float(policy["refined_step_deg"])
    return float(policy["coarse_step_deg"])


def planned_angle_schedule(policy=DEFAULT_SWEEP_POLICY):
    """The angles the policy asks for: coarse to the breakpoint, refined past it."""
    validate_sweep_policy(policy)
    breakpoint_deg = float(policy["step_breakpoint_deg"])
    coarse = float(policy["coarse_step_deg"])
    refined = float(policy["refined_step_deg"])
    ceiling = float(policy["max_sweep_angle_deg"])

    angles = []
    index = 0
    while True:
        angle = _clean_angle(index * coarse)
        if not _at_most(angle, breakpoint_deg):
            break
        angles.append(angle)
        index += 1
    if not angles or not math.isclose(
        angles[-1], breakpoint_deg, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        angles.append(_clean_angle(breakpoint_deg))

    index = 1
    while True:
        angle = _clean_angle(breakpoint_deg + index * refined)
        if not _at_most(angle, ceiling):
            break
        angles.append(angle)
        index += 1
    if not math.isclose(angles[-1], ceiling, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        angles.append(_clean_angle(ceiling))
    return tuple(angles)


def normalise_measured_angles(angles, policy=DEFAULT_SWEEP_POLICY):
    """Sort the measured angles and drop repeats inside the match tolerance."""
    validate_sweep_policy(policy)
    if not isinstance(angles, (list, tuple, set, frozenset)):
        raise ValueError("angles must be a collection of incidence angles")
    validated = sorted(
        _require_incidence_angle("measured_angle_deg", angle) for angle in angles
    )
    tolerance = float(policy["angle_match_tolerance_deg"])
    kept = []
    for angle in validated:
        if kept and abs(angle - kept[-1]) <= tolerance:
            continue
        kept.append(_clean_angle(angle))
    return tuple(kept)


def missing_schedule_angles(measured_angles, policy=DEFAULT_SWEEP_POLICY):
    """Scheduled angles with no measured point inside the match tolerance."""
    validate_sweep_policy(policy)
    measured = normalise_measured_angles(measured_angles, policy)
    tolerance = float(policy["angle_match_tolerance_deg"])
    missing = []
    for wanted in planned_angle_schedule(policy):
        if not any(_at_most(abs(wanted - got), tolerance) for got in measured):
            missing.append(wanted)
    return tuple(missing)


def largest_gap_deg(measured_angles, lower_deg, upper_deg,
                    policy=DEFAULT_SWEEP_POLICY):
    """Widest spacing the sweep leaves inside one region, endpoints included."""
    validate_sweep_policy(policy)
    low = _require_incidence_angle("lower_deg", lower_deg)
    high = _require_incidence_angle("upper_deg", upper_deg)
    if not high > low:
        raise ValueError(
            "upper_deg %g must be above lower_deg %g" % (high, low)
        )
    inside = [
        angle
        for angle in normalise_measured_angles(measured_angles, policy)
        if _at_least(angle, low) and _at_most(angle, high)
    ]
    if len(inside) < 2:
        raise ValueError(
            "a gap needs at least two measured angles between %g and %g degrees"
            % (low, high)
        )
    return max(
        _clean_angle(later - earlier)
        for earlier, later in zip(inside, inside[1:])
    )


def interpolation_error_bound(step_deg, lower_angle_deg):
    """Bound on the straight-line error the cosine law leaves across a step.

    The classic linear-interpolation bound is h^2 / 8 times the largest
    second derivative on the interval; for the cosine that derivative is
    the cosine, largest at the lower angle. The result is a fraction of
    the normal-incidence output.
    """
    step = _require_positive("step_deg", step_deg)
    lower = _require_incidence_angle("lower_angle_deg", lower_angle_deg)
    step_rad = math.radians(step)
    return step_rad * step_rad / 8.0 * math.cos(math.radians(lower))


def worst_interpolation_error(measured_angles, policy=DEFAULT_SWEEP_POLICY):
    """The largest straight-line error any pair of measured angles admits."""
    validate_sweep_policy(policy)
    measured = normalise_measured_angles(measured_angles, policy)
    if len(measured) < 2:
        raise ValueError("an interpolation error needs at least two measured angles")
    return max(
        interpolation_error_bound(_clean_angle(later - earlier), earlier)
        for earlier, later in zip(measured, measured[1:])
        if later > earlier
    )


def sweep_reaches_maximum(measured_angles, policy=DEFAULT_SWEEP_POLICY):
    """True when the sweep gets to the declared maximum angle."""
    validate_sweep_policy(policy)
    measured = normalise_measured_angles(measured_angles, policy)
    if not measured:
        return False
    tolerance = float(policy["angle_match_tolerance_deg"])
    return _at_least(
        measured[-1], float(policy["max_sweep_angle_deg"]) - tolerance
    )


def assess_angular_sweep(case, policy=DEFAULT_SWEEP_POLICY):
    """Full clause 6.4.3.19.2 judgement for one angular sweep."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_sweep_policy(policy)
    if "measured_angles_deg" not in case:
        raise ValueError(
            "case is missing measured_angles_deg; an absent sweep is not an "
            "empty one"
        )
    measured = normalise_measured_angles(case["measured_angles_deg"], policy)
    breakpoint_deg = float(policy["step_breakpoint_deg"])
    ceiling = float(policy["max_sweep_angle_deg"])
    coarse = float(policy["coarse_step_deg"])
    refined = float(policy["refined_step_deg"])
    allowance = float(policy["max_interpolation_error_fraction"])

    findings = []
    result = {
        "schedule_deg": planned_angle_schedule(policy),
        "measured_angles_deg": measured,
        "point_count": len(measured),
        "missing_angles_deg": (),
        "coarse_region_gap_deg": None,
        "refined_region_gap_deg": None,
        "worst_interpolation_error_fraction": None,
        "reaches_maximum": False,
        "findings": findings,
    }

    if len(measured) < 2:
        findings.append(
            "the sweep holds %d measured angle(s); a response against incidence "
            "angle needs a series, not a point" % (len(measured),)
        )
        result["verdict"] = ANGULAR_SWEEP_NOT_PLANNED
        return result

    missing = missing_schedule_angles(measured, policy)
    result["missing_angles_deg"] = missing
    result["reaches_maximum"] = sweep_reaches_maximum(measured, policy)
    result["worst_interpolation_error_fraction"] = worst_interpolation_error(
        measured, policy
    )

    try:
        coarse_gap = largest_gap_deg(measured, 0.0, breakpoint_deg, policy)
    except ValueError:
        coarse_gap = None
        findings.append(
            "fewer than two angles were measured at or below the %g degree "
            "breakpoint, so the coarse region has no sampled interval"
            % (breakpoint_deg,)
        )
    result["coarse_region_gap_deg"] = coarse_gap

    try:
        refined_gap = largest_gap_deg(measured, breakpoint_deg, ceiling, policy)
    except ValueError:
        refined_gap = None
        findings.append(
            "fewer than two angles were measured beyond the %g degree "
            "breakpoint, so the refined region has no sampled interval"
            % (breakpoint_deg,)
        )
    result["refined_region_gap_deg"] = refined_gap

    if coarse_gap is not None and not _at_most(coarse_gap, coarse):
        findings.append(
            "the %s leaves a %.3f deg gap against the %.3f deg step"
            % (COARSE_REGION, coarse_gap, coarse)
        )
    if refined_gap is not None and not _at_most(refined_gap, refined):
        findings.append(
            "the %s leaves a %.3f deg gap against the %.3f deg step"
            % (REFINED_REGION, refined_gap, refined)
        )
    if missing:
        findings.append(
            "%d scheduled angle(s) have no measured point within the match "
            "tolerance: %s"
            % (len(missing), ", ".join("%.3f" % angle for angle in missing))
        )
    if not _at_most(result["worst_interpolation_error_fraction"], allowance):
        findings.append(
            "the widest gap admits a straight-line error of %.5f of the "
            "normal-incidence output against the %.5f allowed"
            % (result["worst_interpolation_error_fraction"], allowance)
        )

    if not result["reaches_maximum"]:
        findings.append(
            "the sweep stops at %.3f deg and the declared maximum is %.3f deg"
            % (measured[-1], ceiling)
        )
        result["verdict"] = ANGULAR_SWEEP_TRUNCATED
        return result
    if findings:
        result["verdict"] = ANGULAR_SWEEP_UNDERSAMPLED
        return result

    result["verdict"] = ANGULAR_SWEEP_ACCEPTED
    return result
