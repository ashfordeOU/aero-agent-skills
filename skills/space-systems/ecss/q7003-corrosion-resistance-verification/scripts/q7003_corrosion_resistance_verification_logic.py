#!/usr/bin/env python3
"""Corrosion-resistance verification of a sealed anodized coating.

Anchor: ECSS-Q-ST-70-03 quality clause on anodizing. The procedure below
is a paraphrase into implementable steps; no standard text is reproduced.

Corrosion resistance of an anodized coating is bought by the seal, not
by the anodic layer on its own. An unsealed layer is porous and takes up
salt as readily as it took up dye, so the verification has two halves
that have to agree:

seal quality   an indirect check on the porosity that is left after
               sealing. The graded quantity is normalised for thickness,
               because a thicker coating presents more sealed area and
               would otherwise look worse than a thin one at the same
               real seal quality.
exposure       a neutral salt fog exposure held for at least the
               required duration, after which the attack on the exposed
               area is counted and sized. Attack is graded by density
               over the exposed area and by the largest single site, so
               one deep pit cannot hide inside an acceptable count and a
               fine scatter cannot hide behind a small maximum.

An exposure that was cut short is not a partial result. The coating is
not credited for time it did not spend under fog, so a short run is
reported as inconclusive rather than as a pass or a failure.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SEAL_GRADES = ("well-sealed", "marginally-sealed", "unsealed")

OUTCOME_PASS = "pass"
OUTCOME_FAIL = "fail"
OUTCOME_INCONCLUSIVE = "inconclusive"

# Thickness the normalised seal admittance is referred to.
REFERENCE_THICKNESS_UM = 20.0

DEFAULT_SEAL_LIMITS = {
    "well_sealed_max_us": 20.0,
    "marginal_max_us": 40.0,
}

DEFAULT_ATTACK_LIMITS = {
    "max_sites_per_dm2": 2.0,
    "max_site_size_mm": 0.8,
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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A normalised admittance is a ratio of two measured quantities, so a
    coupon that was meant to land exactly on a limit can evaluate a few
    units in the last place above it. The limit is never raised; only
    the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_seal_limits(limits):
    """Check a seal-grading limit set is ordered and positive."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    well = _require_positive("well_sealed_max_us", limits.get("well_sealed_max_us"))
    marginal = _require_positive("marginal_max_us", limits.get("marginal_max_us"))
    if marginal < well:
        raise ValueError(
            "marginal_max_us %g must not be below well_sealed_max_us %g"
            % (marginal, well)
        )
    return limits


def normalised_admittance_us(admittance_us, thickness_um):
    """Seal admittance referred to the reference coating thickness.

    A thicker coating carries more sealed pore area, so its raw
    admittance reads high at the same real seal quality. Referring the
    reading to a common thickness makes two coupons comparable.
    """
    admittance = _require_non_negative("admittance_us", admittance_us)
    thickness = _require_positive("thickness_um", thickness_um)
    return admittance * REFERENCE_THICKNESS_UM / thickness


def grade_seal(admittance_us, thickness_um, limits=DEFAULT_SEAL_LIMITS):
    """Group the seal as well-sealed, marginally-sealed or unsealed."""
    validate_seal_limits(limits)
    normalised = normalised_admittance_us(admittance_us, thickness_um)
    if _at_most(normalised, limits["well_sealed_max_us"]):
        grade = "well-sealed"
    elif _at_most(normalised, limits["marginal_max_us"]):
        grade = "marginally-sealed"
    else:
        grade = "unsealed"
    findings = []
    if grade == "marginally-sealed":
        findings.append(
            "normalised admittance %.3f uS sits between the sealed and unsealed "
            "limits; the seal step needs a dwell or temperature review"
            % normalised
        )
    elif grade == "unsealed":
        findings.append(
            "normalised admittance %.3f uS is above the %.3f uS unsealed limit; "
            "the coating is effectively open"
            % (normalised, limits["marginal_max_us"])
        )
    return {
        "raw_admittance_us": float(admittance_us),
        "normalised_admittance_us": normalised,
        "grade": grade,
        "findings": findings,
    }


def attack_density_per_dm2(site_count, exposed_area_mm2):
    """Attack sites per square decimetre of exposed area."""
    count = _require_count("site_count", site_count)
    area = _require_positive("exposed_area_mm2", exposed_area_mm2)
    return count / (area / 10000.0)


def evaluate_attack(
    site_count, exposed_area_mm2, largest_site_mm=0.0, limits=DEFAULT_ATTACK_LIMITS
):
    """Grade corrosion attack by density over the area and by worst site."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    max_density = _require_non_negative(
        "max_sites_per_dm2", limits.get("max_sites_per_dm2")
    )
    max_size = _require_non_negative(
        "max_site_size_mm", limits.get("max_site_size_mm")
    )
    count = _require_count("site_count", site_count)
    largest = _require_non_negative("largest_site_mm", largest_site_mm)
    if count == 0 and largest > 0.0:
        raise ValueError(
            "a largest site of %g mm was recorded with a zero site count" % largest
        )
    density = attack_density_per_dm2(count, exposed_area_mm2)
    findings = []
    density_ok = _at_most(density, max_density)
    size_ok = _at_most(largest, max_size)
    if not density_ok:
        findings.append(
            "attack density %.3f sites/dm2 exceeds the %.3f allowance"
            % (density, max_density)
        )
    if not size_ok:
        findings.append(
            "largest attack site %.3f mm exceeds the %.3f mm allowance"
            % (largest, max_size)
        )
    return {
        "site_count": count,
        "density_per_dm2": density,
        "largest_site_mm": largest,
        "density_acceptable": density_ok,
        "size_acceptable": size_ok,
        "outcome": OUTCOME_PASS if (density_ok and size_ok) else OUTCOME_FAIL,
        "findings": findings,
    }


def exposure_is_sufficient(actual_hours, required_hours):
    """Whether the salt fog exposure ran for at least the required time."""
    actual = _require_non_negative("actual_hours", actual_hours)
    required = _require_positive("required_hours", required_hours)
    return _at_least(actual, required)


def verify_corrosion_resistance(
    case, seal_limits=DEFAULT_SEAL_LIMITS, attack_limits=DEFAULT_ATTACK_LIMITS
):
    """Full corrosion-resistance verdict for a sealed anodized coupon set."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    seal = grade_seal(
        case.get("seal_admittance_us"), case.get("thickness_um"), seal_limits
    )
    sufficient = exposure_is_sufficient(
        case.get("exposure_hours"), case.get("required_exposure_hours")
    )
    findings = list(seal["findings"])
    if not sufficient:
        findings.append(
            "salt fog exposure of %g h is short of the %g h required; the coating "
            "is not credited for time it did not spend under fog"
            % (
                _require_non_negative("exposure_hours", case.get("exposure_hours")),
                _require_positive(
                    "required_exposure_hours", case.get("required_exposure_hours")
                ),
            )
        )
        return {
            "outcome": OUTCOME_INCONCLUSIVE,
            "exposure_sufficient": False,
            "seal": seal,
            "attack": None,
            "findings": findings,
        }
    attack = evaluate_attack(
        case.get("site_count"),
        case.get("exposed_area_mm2"),
        largest_site_mm=case.get("largest_site_mm", 0.0),
        limits=attack_limits,
    )
    findings.extend(attack["findings"])
    if attack["outcome"] == OUTCOME_FAIL or seal["grade"] == "unsealed":
        outcome = OUTCOME_FAIL
    else:
        outcome = OUTCOME_PASS
    if seal["grade"] == "unsealed" and attack["outcome"] == OUTCOME_PASS:
        findings.append(
            "the coupon survived the exposure on an unsealed coating; the result "
            "does not carry to production parts with a different exposed area"
        )
    return {
        "outcome": outcome,
        "exposure_sufficient": True,
        "seal": seal,
        "attack": attack,
        "findings": findings,
    }
