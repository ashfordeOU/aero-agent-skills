#!/usr/bin/env python3
"""Solvent rinse and wipe extraction for indirect contamination measurement.

Anchor: ECSS-Q-ST-70-05C, the indirect-method clauses covering the
removal of surface contamination into a solvent by rinsing or wiping.
The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

The indirect method measures a residue and reports a surface. Getting
from one to the other is arithmetic that has to be done explicitly,
because every step of it loses material.

A single pass removes a fraction of what is on the surface, not all of
it, and the next pass removes the same fraction of what is left. Over n
passes the cumulative recovery is one minus the unremoved fraction
raised to n: it climbs fast at first and then stops being worth another
pass. The number of passes needed for a target recovery falls out of the
same expression, inverted.

The rinse volume has to suit the area. Too little and the solvent
saturates and stops wetting; too much and the residue is spread so thin
that the concentration step cannot bring it back above the cell's
quantitation limit.

The areal contamination level is the residue mass divided by the
sampled area and by the cumulative recovery. Leaving the recovery out
does not make the answer conservative: it makes it low, which is the
wrong direction for a cleanliness verification.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DEFAULT_EXTRACTION_POLICY = {
    "min_volume_per_area_ml_cm2": 0.02,
    "max_volume_per_area_ml_cm2": 0.50,
    "min_sampled_area_cm2": 25.0,
    "min_cumulative_recovery": 0.75,
    "cell_quantitation_limit_ug": 30.0,
    "max_concentration_factor": 50.0,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError("%s must sit in (0, 1], got %r" % (name, value))
    return number


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_passes(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(
            "%s must be an integer of at least 1, got %r" % (name, value)
        )
    return value


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


def validate_extraction_policy(policy):
    """Check an extraction policy carries a usable volume band and floors."""
    _require_mapping("policy", policy)
    low = _require_positive(
        "min_volume_per_area_ml_cm2", policy.get("min_volume_per_area_ml_cm2")
    )
    high = _require_positive(
        "max_volume_per_area_ml_cm2", policy.get("max_volume_per_area_ml_cm2")
    )
    if high <= low:
        raise ValueError(
            "max_volume_per_area_ml_cm2 %g must sit above the minimum %g"
            % (high, low)
        )
    _require_positive("min_sampled_area_cm2", policy.get("min_sampled_area_cm2"))
    _require_fraction(
        "min_cumulative_recovery", policy.get("min_cumulative_recovery")
    )
    _require_positive(
        "cell_quantitation_limit_ug", policy.get("cell_quantitation_limit_ug")
    )
    factor = _require_positive(
        "max_concentration_factor", policy.get("max_concentration_factor")
    )
    if factor < 1.0:
        raise ValueError(
            "max_concentration_factor %g would forbid concentrating at all"
            % factor
        )
    return policy


def cumulative_recovery(per_pass_fraction, passes):
    """Fraction of the surface load n passes take up between them.

    Each pass removes the same fraction of what is still there, so the
    unremoved part shrinks geometrically and the recovery is one minus it.
    """
    fraction = _require_fraction("per_pass_fraction", per_pass_fraction)
    count = _require_passes("passes", passes)
    remaining = 1.0
    for _ in range(count):
        remaining *= 1.0 - fraction
    return 1.0 - remaining


def passes_for_target_recovery(per_pass_fraction, target_recovery):
    """Smallest number of passes reaching a target cumulative recovery."""
    fraction = _require_fraction("per_pass_fraction", per_pass_fraction)
    target = _require_number("target_recovery", target_recovery)
    if not 0.0 < target < 1.0:
        raise ValueError(
            "target_recovery must sit strictly inside (0, 1); a complete "
            "recovery is never reached in finitely many passes, got %r"
            % (target_recovery,)
        )
    if fraction == 1.0:
        return 1
    count = 1
    while not _at_least(cumulative_recovery(fraction, count), target):
        count += 1
        if count > 1000:
            raise ValueError(
                "target_recovery %g is not reachable in a practical number of "
                "passes at a per-pass fraction of %g" % (target, fraction)
            )
    return count


def volume_per_area_ml_cm2(rinse_volume_ml, sampled_area_cm2):
    """Rinse volume spread over the area it has to wet."""
    volume = _require_positive("rinse_volume_ml", rinse_volume_ml)
    area = _require_positive("sampled_area_cm2", sampled_area_cm2)
    return volume / area


def rinse_volume_check(
    rinse_volume_ml, sampled_area_cm2, policy=DEFAULT_EXTRACTION_POLICY
):
    """Whether the rinse volume suits the sampled area."""
    validate_extraction_policy(policy)
    area = _require_positive("sampled_area_cm2", sampled_area_cm2)
    if not _at_least(area, policy["min_sampled_area_cm2"]):
        raise ValueError(
            "sampled_area_cm2 %g is below the policy floor %g; too little area "
            "puts the residue under the cell limit by construction"
            % (area, policy["min_sampled_area_cm2"])
        )
    ratio = volume_per_area_ml_cm2(rinse_volume_ml, area)
    too_low = not _at_least(ratio, policy["min_volume_per_area_ml_cm2"])
    too_high = not _at_most(ratio, policy["max_volume_per_area_ml_cm2"])
    reason = None
    if too_low:
        reason = (
            "%.4g ml/cm2 is below the wetting floor %.4g; the solvent saturates "
            "before it has covered the area"
            % (ratio, policy["min_volume_per_area_ml_cm2"])
        )
    elif too_high:
        reason = (
            "%.4g ml/cm2 is above the ceiling %.4g; the residue is diluted "
            "further than the concentration step can recover"
            % (ratio, policy["max_volume_per_area_ml_cm2"])
        )
    return {
        "volume_per_area_ml_cm2": ratio,
        "acceptable": not (too_low or too_high),
        "reason": reason,
    }


def concentration_factor(initial_volume_ml, final_volume_ml):
    """How far the extract is concentrated before it reaches the cell."""
    initial = _require_positive("initial_volume_ml", initial_volume_ml)
    final = _require_positive("final_volume_ml", final_volume_ml)
    if final > initial:
        raise ValueError(
            "final_volume_ml %g exceeds initial_volume_ml %g; concentrating "
            "cannot increase the volume" % (final, initial)
        )
    return initial / final


def areal_contamination_ug_cm2(residue_mass_ug, sampled_area_cm2, recovery):
    """Surface level the measured residue implies, corrected for recovery."""
    mass = _require_positive("residue_mass_ug", residue_mass_ug)
    area = _require_positive("sampled_area_cm2", sampled_area_cm2)
    fraction = _require_fraction("recovery", recovery)
    return mass / (area * fraction)


def expected_residue_mass_ug(areal_level_ug_cm2, sampled_area_cm2, recovery):
    """Residue a known surface level would put into the extract."""
    level = _require_positive("areal_level_ug_cm2", areal_level_ug_cm2)
    area = _require_positive("sampled_area_cm2", sampled_area_cm2)
    fraction = _require_fraction("recovery", recovery)
    return level * area * fraction


def extract_surface_contamination(case, policy=DEFAULT_EXTRACTION_POLICY):
    """Full extraction result: recovery, volumes, and the surface level."""
    validate_extraction_policy(policy)
    _require_mapping("case", case)
    recovery = cumulative_recovery(
        case.get("per_pass_fraction"), case.get("passes")
    )
    volume = rinse_volume_check(
        case.get("rinse_volume_ml"), case.get("sampled_area_cm2"), policy
    )
    factor = concentration_factor(
        case.get("rinse_volume_ml"), case.get("final_volume_ml")
    )
    residue = _require_positive("residue_mass_ug", case.get("residue_mass_ug"))
    corrected = areal_contamination_ug_cm2(
        residue, case.get("sampled_area_cm2"), recovery
    )
    uncorrected = residue / _require_positive(
        "sampled_area_cm2", case.get("sampled_area_cm2")
    )

    findings = []
    duties = []
    if not _at_least(recovery, policy["min_cumulative_recovery"]):
        findings.append(
            "%d passes at %.2f per pass recover only %.3f of the surface load "
            "against a required %.3f; add passes rather than correcting a large "
            "unknown away"
            % (
                case["passes"],
                case["per_pass_fraction"],
                recovery,
                policy["min_cumulative_recovery"],
            )
        )
    if not volume["acceptable"]:
        findings.append("the rinse volume does not suit the area: %s" % volume["reason"])
    if not _at_most(factor, policy["max_concentration_factor"]):
        findings.append(
            "a concentration factor of %.1f exceeds the ceiling %.1f, so the "
            "extract carries its own solvent residue up with the sample"
            % (factor, policy["max_concentration_factor"])
        )
    if not _at_least(residue, policy["cell_quantitation_limit_ug"]):
        findings.append(
            "the residue reaching the cell is %.2f ug against a quantitation "
            "limit of %.2f ug; the number is a detection, not a measurement"
            % (residue, policy["cell_quantitation_limit_ug"])
        )
    duties.append(
        "report the areal level corrected for the %.3f cumulative recovery; the "
        "uncorrected %.4g ug/cm2 understates the surface by the same factor"
        % (recovery, uncorrected)
    )
    duties.append(
        "state the pass count and per-pass fraction the recovery came from, so "
        "a later run with a different technique is comparable"
    )
    return {
        "cumulative_recovery": recovery,
        "volume_check": volume,
        "concentration_factor": factor,
        "residue_mass_ug": residue,
        "uncorrected_level_ug_cm2": uncorrected,
        "areal_level_ug_cm2": corrected,
        "duties": duties,
        "findings": findings,
        "extraction_sound": not findings,
    }
