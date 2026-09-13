#!/usr/bin/env python3
"""Electrical performance criteria for a solar cell assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.3.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause turns a measured current into a pass or a fail against two
minimum values -- one before electron irradiation and one after it --
and it fixes where those minima come from: the control drawing for the
assembly, not the datasheet, not the supplier's typical figure and not
a value carried over from a previous build. The source is part of the
criterion, because a minimum with no drawing behind it cannot be shown
to be the one the design was accepted against.

Three things then decide the outcome:

    the limits      a pair taken from the drawing, with the
                    post-irradiation minimum at or below the
                    pre-irradiation one. A drawing that allows no
                    degradation at all, or demands the assembly gain
                    current under irradiation, is self-contradictory
                    and is refused rather than applied.
    the exposure    the post-irradiation minimum is only a criterion at
                    the fluence the drawing qualifies. A measurement
                    taken after a lighter exposure does not demonstrate
                    it, however high the current comes out.
    the currents    each measured value against its own minimum, with a
                    guard band the size of the measurement uncertainty.
                    A value inside that band is neither a pass nor a
                    fail; it is a result the measurement cannot resolve,
                    and calling it either way invents precision.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONTROL_DRAWING = "solar-cell-assembly-control-drawing"

LIMIT_SOURCE_NOT_ACCEPTED = "limit-source-not-accepted"
DRAWING_LIMITS_NOT_CREDIBLE = "drawing-limits-not-credible"
IRRADIATION_NOT_DEMONSTRATED = "irradiation-not-demonstrated"
BELOW_MINIMUM_CURRENT = "below-minimum-current"
WITHIN_MEASUREMENT_UNCERTAINTY = "within-measurement-uncertainty"
PERFORMANCE_CRITERIA_MET = "performance-criteria-met"

ABOVE_MINIMUM = "above-minimum"
UNRESOLVED_AGAINST_MINIMUM = "unresolved-against-minimum"
BELOW_MINIMUM = "below-minimum"

DEFAULT_CRITERIA_POLICY = {
    "accepted_limit_sources": (CONTROL_DRAWING,),
    "measurement_uncertainty_fraction": 0.01,
    "min_retention_fraction": 0.70,
    "max_retention_fraction": 1.0,
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


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


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


def validate_criteria_policy(policy):
    """Check an acceptance policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    sources = policy.get("accepted_limit_sources")
    if not isinstance(sources, (list, tuple)) or not sources:
        raise ValueError(
            "accepted_limit_sources must be a non-empty collection, got %r"
            % (sources,)
        )
    for source in sources:
        _require_text("accepted limit source", source)
    _require_non_negative(
        "measurement_uncertainty_fraction",
        policy.get("measurement_uncertainty_fraction"),
    )
    low = _require_positive("min_retention_fraction", policy.get("min_retention_fraction"))
    high = _require_positive(
        "max_retention_fraction", policy.get("max_retention_fraction")
    )
    if high < low:
        raise ValueError(
            "max_retention_fraction %g is below min_retention_fraction %g"
            % (high, low)
        )
    return policy


def limit_source_accepted(source, policy=DEFAULT_CRITERIA_POLICY):
    """True when the minima come from a source the policy accepts."""
    validate_criteria_policy(policy)
    named = _require_text("limit source", source)
    return named in tuple(policy["accepted_limit_sources"])


def validate_control_drawing_limits(limits, policy=DEFAULT_CRITERIA_POLICY):
    """Check the pair of minima taken from the drawing can be applied."""
    validate_criteria_policy(policy)
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    _require_text("limits source", limits.get("source"))
    _require_text("limits drawing_reference", limits.get("drawing_reference"))
    before = _require_positive(
        "min_current_before_a", limits.get("min_current_before_a")
    )
    after = _require_positive("min_current_after_a", limits.get("min_current_after_a"))
    if after > before and not math.isclose(
        after, before, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "the post-irradiation minimum %g A stands above the "
            "pre-irradiation minimum %g A; electron irradiation does not add "
            "current" % (after, before)
        )
    _require_positive(
        "qualification_fluence_e_per_cm2",
        limits.get("qualification_fluence_e_per_cm2"),
    )
    return limits


def retention_fraction(after_a, before_a):
    """What share of the pre-irradiation current the after value keeps."""
    after = _require_non_negative("after_a", after_a)
    before = _require_positive("before_a", before_a)
    return after / before


def degradation_fraction(after_a, before_a):
    """What share of the pre-irradiation current the exposure removed."""
    return 1.0 - retention_fraction(after_a, before_a)


def margin_fraction(measured_a, minimum_a):
    """Signed margin of a measured current over its minimum."""
    measured = _require_non_negative("measured_a", measured_a)
    minimum = _require_positive("minimum_a", minimum_a)
    return (measured - minimum) / minimum


def guard_band_a(minimum_a, policy=DEFAULT_CRITERIA_POLICY):
    """Half-width the measurement uncertainty puts around a minimum."""
    validate_criteria_policy(policy)
    minimum = _require_positive("minimum_a", minimum_a)
    return minimum * float(policy["measurement_uncertainty_fraction"])


def current_outcome(measured_a, minimum_a, policy=DEFAULT_CRITERIA_POLICY):
    """Grouped outcome of one measured current against one minimum."""
    band = guard_band_a(minimum_a, policy)
    measured = _require_non_negative("measured_a", measured_a)
    minimum = float(minimum_a)
    if _at_least(measured, minimum + band):
        return ABOVE_MINIMUM
    if _at_least(measured, minimum - band):
        return UNRESOLVED_AGAINST_MINIMUM
    return BELOW_MINIMUM


def drawing_retention_is_sensible(limits, policy=DEFAULT_CRITERIA_POLICY):
    """True when the drawing's own pair allows a credible degradation."""
    validate_control_drawing_limits(limits, policy)
    fraction = retention_fraction(
        limits["min_current_after_a"], limits["min_current_before_a"]
    )
    return _at_least(fraction, float(policy["min_retention_fraction"])) and _at_most(
        fraction, float(policy["max_retention_fraction"])
    )


def fluence_demonstrates_criterion(
    delivered_fluence_e_per_cm2, limits, policy=DEFAULT_CRITERIA_POLICY
):
    """True when the exposure reached the fluence the drawing qualifies."""
    validate_control_drawing_limits(limits, policy)
    delivered = _require_positive(
        "delivered_fluence_e_per_cm2", delivered_fluence_e_per_cm2
    )
    return _at_least(delivered, float(limits["qualification_fluence_e_per_cm2"]))


def assess_electrical_performance_criteria(case, policy=DEFAULT_CRITERIA_POLICY):
    """Full clause 6.4.3.3.3 judgement for one assembly's measured currents."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_criteria_policy(policy)
    limits = validate_control_drawing_limits(case.get("limits"), policy)
    if "delivered_fluence_e_per_cm2" not in case:
        raise ValueError(
            "case is missing delivered_fluence_e_per_cm2; an unstated exposure "
            "is not a zero one"
        )
    delivered = _require_positive(
        "case delivered_fluence_e_per_cm2", case.get("delivered_fluence_e_per_cm2")
    )
    measured_before = _require_non_negative(
        "case measured_current_before_a", case.get("measured_current_before_a")
    )
    measured_after = _require_non_negative(
        "case measured_current_after_a", case.get("measured_current_after_a")
    )

    minimum_before = float(limits["min_current_before_a"])
    minimum_after = float(limits["min_current_after_a"])
    findings = []
    result = {
        "limit_source": limits["source"],
        "drawing_reference": limits["drawing_reference"],
        "min_current_before_a": minimum_before,
        "min_current_after_a": minimum_after,
        "drawing_retention_fraction": retention_fraction(
            minimum_after, minimum_before
        ),
        "measured_retention_fraction": None,
        "measured_degradation_fraction": None,
        "margin_before_fraction": margin_fraction(measured_before, minimum_before),
        "margin_after_fraction": margin_fraction(measured_after, minimum_after),
        "before_outcome": current_outcome(measured_before, minimum_before, policy),
        "after_outcome": current_outcome(measured_after, minimum_after, policy),
        "fluence_demonstrates_criterion": fluence_demonstrates_criterion(
            delivered, limits, policy
        ),
        "findings": findings,
    }
    if measured_before > 0.0:
        result["measured_retention_fraction"] = retention_fraction(
            measured_after, measured_before
        )
        result["measured_degradation_fraction"] = degradation_fraction(
            measured_after, measured_before
        )

    if not limit_source_accepted(limits["source"], policy):
        findings.append(
            "the minima are taken from %r, not from the control drawing the "
            "clause names as their source" % limits["source"]
        )
        result["verdict"] = LIMIT_SOURCE_NOT_ACCEPTED
        return result

    if not drawing_retention_is_sensible(limits, policy):
        findings.append(
            "the drawing's own pair keeps %.4g of the pre-irradiation current "
            "after exposure, outside the %.4g to %.4g a credible criterion "
            "spans"
            % (
                result["drawing_retention_fraction"],
                float(policy["min_retention_fraction"]),
                float(policy["max_retention_fraction"]),
            )
        )
        result["verdict"] = DRAWING_LIMITS_NOT_CREDIBLE
        return result

    if not result["fluence_demonstrates_criterion"]:
        findings.append(
            "the exposure delivered %.4g electrons per square centimetre "
            "against the %.4g the drawing qualifies, so the after measurement "
            "does not demonstrate the post-irradiation minimum"
            % (delivered, float(limits["qualification_fluence_e_per_cm2"]))
        )
        result["verdict"] = IRRADIATION_NOT_DEMONSTRATED
        return result

    if result["before_outcome"] == BELOW_MINIMUM:
        findings.append(
            "the pre-irradiation current %.4g A stands below the %.4g A "
            "minimum" % (measured_before, minimum_before)
        )
    if result["after_outcome"] == BELOW_MINIMUM:
        findings.append(
            "the post-irradiation current %.4g A stands below the %.4g A "
            "minimum" % (measured_after, minimum_after)
        )
    if BELOW_MINIMUM in (result["before_outcome"], result["after_outcome"]):
        result["verdict"] = BELOW_MINIMUM_CURRENT
        return result

    if UNRESOLVED_AGAINST_MINIMUM in (
        result["before_outcome"],
        result["after_outcome"],
    ):
        findings.append(
            "a measured current sits inside the measurement uncertainty of its "
            "minimum, so the run resolves neither a pass nor a fail"
        )
        result["verdict"] = WITHIN_MEASUREMENT_UNCERTAINTY
        return result

    result["verdict"] = PERFORMANCE_CRITERIA_MET
    return result
