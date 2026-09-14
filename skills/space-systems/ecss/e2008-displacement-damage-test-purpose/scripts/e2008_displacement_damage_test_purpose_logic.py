#!/usr/bin/env python3
"""Purpose of the non-ionising exposure asked of displacement-sensitive parts.

Anchor: ECSS-E-ST-20-08C clause 12.6.11.2.1. The reasoning below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause exists because ionising dose is not the whole radiation
story. A total-dose campaign charges oxides and shifts surfaces. It
says nothing about what an energetic particle does when it knocks a
lattice atom off its site, and that second mechanism -- displacement
damage -- is the one that kills a part whose current has to cross a
neutral base.

Which technologies care is not a matter of taste. Displacement damage
works by introducing recombination centres, and recombination centres
cost minority-carrier lifetime. A device whose current is carried by
majority carriers barely notices; a device that has to move injected
minority carriers across a base before they recombine notices
immediately, because its base transport is exactly the thing the damage
attacks.

The arithmetic that makes this decidable:

    Messenger-Spratt     1/tau = 1/tau0 + K * fluence
    diffusion length     L = sqrt(D * tau)
    damage dose          DDD = fluence * NIEL
    equivalence          a test fluence is worth a reference fluence in
                         the ratio of their non-ionising energy losses

A part stays healthy while its post-exposure diffusion length still
covers its base with margin. Once L falls toward the base width the
injected carriers recombine before they arrive, and the forward drop,
the stored charge and the reverse recovery all move together.

What this module decides:

    sensitivity     whether this technology owes a non-ionising
                    exposure at all, and on what grounds
    size            the fluence such an exposure has to reach, in the
                    equivalence the mission budget is written in
    adequacy        whether a proposed plan gets there, with enough
                    parts to mean anything

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MINORITY_CARRIER = "minority-carrier-conduction"
MAJORITY_CARRIER = "majority-carrier-conduction"
_CARRIER_TYPES = (MINORITY_CARRIER, MAJORITY_CARRIER)

EXPOSURE_NOT_REQUIRED = "non-ionising-exposure-not-required"
EXPOSURE_REQUIRED_PLAN_MISSING = "non-ionising-exposure-required-plan-missing"
EXPOSURE_REQUIRED_PLAN_SHORT = "non-ionising-exposure-required-plan-short"
EXPOSURE_REQUIRED_PLAN_ACCEPTED = "non-ionising-exposure-required-plan-accepted"

DEFAULT_DISPLACEMENT_POLICY = {
    "reference_niel_mev_cm2_per_g": 2.0e-3,
    "base_transport_margin": 3.0,
    "min_lifetime_retention": 0.5,
    "test_fluence_margin_factor": 1.5,
    "min_sample_count": 5,
}

_CM_PER_UM = 1.0e-4
_UM_PER_CM = 1.0e4

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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return number


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_displacement_policy(policy):
    """Check the displacement-damage policy is complete and consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "reference_niel_mev_cm2_per_g", policy.get("reference_niel_mev_cm2_per_g")
    )
    margin = _require_positive(
        "base_transport_margin", policy.get("base_transport_margin")
    )
    if margin < 1.0:
        raise ValueError(
            "base_transport_margin %g would accept a diffusion length shorter "
            "than the base it has to cross" % (margin,)
        )
    _require_fraction(
        "min_lifetime_retention", policy.get("min_lifetime_retention")
    )
    factor = _require_positive(
        "test_fluence_margin_factor", policy.get("test_fluence_margin_factor")
    )
    if factor < 1.0:
        raise ValueError(
            "test_fluence_margin_factor %g would stop the exposure short of "
            "the end-of-life point it stands in for" % (factor,)
        )
    count = _require_count("min_sample_count", policy.get("min_sample_count"))
    if count < 1:
        raise ValueError("min_sample_count must be at least one part")
    return policy


def validate_technology_profile(profile):
    """Refuse a technology description that cannot be reasoned about."""
    if not isinstance(profile, dict):
        raise ValueError("profile must be a mapping, got %r" % (profile,))
    _require_text("technology", profile.get("technology"))
    carrier = profile.get("carrier_type")
    if carrier not in _CARRIER_TYPES:
        raise ValueError(
            "carrier_type must be one of %s, got %r" % (list(_CARRIER_TYPES), carrier)
        )
    _require_positive(
        "base_lifetime_s", profile.get("base_lifetime_s")
    )
    _require_positive(
        "damage_constant_cm2_per_s", profile.get("damage_constant_cm2_per_s")
    )
    _require_positive(
        "diffusivity_cm2_per_s", profile.get("diffusivity_cm2_per_s")
    )
    _require_positive("base_width_um", profile.get("base_width_um"))
    return profile


def validate_mission_environment(mission):
    """Refuse an environment with no end-of-life particle fluence to stand in for."""
    if not isinstance(mission, dict):
        raise ValueError("mission must be a mapping, got %r" % (mission,))
    _require_positive(
        "end_of_life_fluence_per_cm2", mission.get("end_of_life_fluence_per_cm2")
    )
    _require_positive("niel_mev_cm2_per_g", mission.get("niel_mev_cm2_per_g"))
    return mission


def validate_exposure_plan(plan):
    """Refuse a proposed non-ionising exposure that states no level or population."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    _require_text("particle", plan.get("particle"))
    _require_positive(
        "planned_fluence_per_cm2", plan.get("planned_fluence_per_cm2")
    )
    _require_positive("niel_mev_cm2_per_g", plan.get("niel_mev_cm2_per_g"))
    _require_count("sample_count", plan.get("sample_count"))
    return plan


def displacement_damage_dose(fluence_per_cm2, niel_mev_cm2_per_g):
    """Non-ionising dose a fluence deposits, in MeV per gram."""
    fluence = _require_non_negative("fluence_per_cm2", fluence_per_cm2)
    niel = _require_positive("niel_mev_cm2_per_g", niel_mev_cm2_per_g)
    return fluence * niel


def equivalent_fluence(fluence_per_cm2, niel_mev_cm2_per_g, reference_niel):
    """A fluence restated in the equivalence the mission budget is written in."""
    fluence = _require_non_negative("fluence_per_cm2", fluence_per_cm2)
    niel = _require_positive("niel_mev_cm2_per_g", niel_mev_cm2_per_g)
    reference = _require_positive("reference_niel", reference_niel)
    return fluence * niel / reference


def degraded_lifetime_s(base_lifetime_s, damage_constant_cm2_per_s, fluence_per_cm2):
    """Minority-carrier lifetime left after a fluence, by the Messenger-Spratt law."""
    tau_zero = _require_positive("base_lifetime_s", base_lifetime_s)
    constant = _require_positive(
        "damage_constant_cm2_per_s", damage_constant_cm2_per_s
    )
    fluence = _require_non_negative("fluence_per_cm2", fluence_per_cm2)
    return 1.0 / (1.0 / tau_zero + constant * fluence)


def lifetime_retention(base_lifetime_s, damage_constant_cm2_per_s, fluence_per_cm2):
    """Share of the starting minority-carrier lifetime the part keeps."""
    tau_zero = _require_positive("base_lifetime_s", base_lifetime_s)
    return (
        degraded_lifetime_s(tau_zero, damage_constant_cm2_per_s, fluence_per_cm2)
        / tau_zero
    )


def diffusion_length_um(diffusivity_cm2_per_s, lifetime_s):
    """Distance an injected carrier covers before it recombines, in micrometres."""
    diffusivity = _require_positive("diffusivity_cm2_per_s", diffusivity_cm2_per_s)
    lifetime = _require_positive("lifetime_s", lifetime_s)
    return math.sqrt(diffusivity * lifetime) * _UM_PER_CM


def base_transport_ratio(profile, fluence_per_cm2):
    """Post-exposure diffusion length as a multiple of the base it has to cross."""
    validate_technology_profile(profile)
    lifetime = degraded_lifetime_s(
        profile["base_lifetime_s"],
        profile["damage_constant_cm2_per_s"],
        fluence_per_cm2,
    )
    length_um = diffusion_length_um(profile["diffusivity_cm2_per_s"], lifetime)
    return length_um / float(profile["base_width_um"])


def assess_sensitivity(profile, mission, policy=DEFAULT_DISPLACEMENT_POLICY):
    """Decide whether this technology owes a non-ionising exposure, and why."""
    validate_displacement_policy(policy)
    validate_technology_profile(profile)
    validate_mission_environment(mission)

    fluence = float(mission["end_of_life_fluence_per_cm2"])
    reasons = []
    result = {
        "technology": profile["technology"],
        "carrier_type": profile["carrier_type"],
        "end_of_life_fluence_per_cm2": fluence,
        "displacement_damage_dose_mev_per_g": displacement_damage_dose(
            fluence, mission["niel_mev_cm2_per_g"]
        ),
        "lifetime_retention": None,
        "base_transport_ratio": None,
        "reasons": reasons,
    }

    if profile["carrier_type"] == MAJORITY_CARRIER:
        reasons.append(
            "%s carries its current on majority carriers, so lost "
            "minority-carrier lifetime does not reach its transport"
            % (profile["technology"],)
        )
        result["sensitive"] = False
        return result

    retention = lifetime_retention(
        profile["base_lifetime_s"],
        profile["damage_constant_cm2_per_s"],
        fluence,
    )
    ratio = base_transport_ratio(profile, fluence)
    result["lifetime_retention"] = retention
    result["base_transport_ratio"] = ratio

    min_retention = float(policy["min_lifetime_retention"])
    min_ratio = float(policy["base_transport_margin"])

    if not _at_least(retention, min_retention):
        reasons.append(
            "minority-carrier lifetime falls to %.4f of its starting value "
            "against the %.4f the policy allows" % (retention, min_retention)
        )
    if not _at_least(ratio, min_ratio):
        reasons.append(
            "the diffusion length ends at %.3f base widths against the %.3f "
            "the policy asks be kept" % (ratio, min_ratio)
        )

    result["sensitive"] = bool(reasons)
    if not reasons:
        reasons.append(
            "%s keeps %.4f of its lifetime and %.3f base widths of diffusion "
            "length at the end-of-life fluence"
            % (profile["technology"], retention, ratio)
        )
    return result


def required_test_fluence(mission, policy=DEFAULT_DISPLACEMENT_POLICY):
    """Equivalent fluence a standing-in exposure has to reach, margin included."""
    validate_displacement_policy(policy)
    validate_mission_environment(mission)
    reference = float(policy["reference_niel_mev_cm2_per_g"])
    end_of_life = equivalent_fluence(
        mission["end_of_life_fluence_per_cm2"],
        mission["niel_mev_cm2_per_g"],
        reference,
    )
    return end_of_life * float(policy["test_fluence_margin_factor"])


def assess_displacement_damage_purpose(case, policy=DEFAULT_DISPLACEMENT_POLICY):
    """Full clause 12.6.11.2.1 judgement: is the exposure owed, and does the plan meet it."""
    validate_displacement_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    if "technology" not in case:
        raise ValueError(
            "case is missing technology; the clause turns on what carries the "
            "current, not on the part number"
        )
    if "mission" not in case:
        raise ValueError(
            "case is missing mission; an exposure stands in for an environment "
            "and there is none stated"
        )

    sensitivity = assess_sensitivity(case["technology"], case["mission"], policy)
    required = required_test_fluence(case["mission"], policy)
    findings = list(sensitivity["reasons"])

    result = {
        "technology": sensitivity["technology"],
        "sensitive": sensitivity["sensitive"],
        "lifetime_retention": sensitivity["lifetime_retention"],
        "base_transport_ratio": sensitivity["base_transport_ratio"],
        "displacement_damage_dose_mev_per_g": sensitivity[
            "displacement_damage_dose_mev_per_g"
        ],
        "required_equivalent_fluence_per_cm2": required,
        "planned_equivalent_fluence_per_cm2": None,
        "findings": findings,
    }

    if not sensitivity["sensitive"]:
        result["verdict"] = EXPOSURE_NOT_REQUIRED
        return result

    plan = case.get("plan")
    if plan is None:
        findings.append(
            "the technology is sensitive to displacement damage and no "
            "non-ionising exposure is planned"
        )
        result["verdict"] = EXPOSURE_REQUIRED_PLAN_MISSING
        return result

    validate_exposure_plan(plan)
    planned = equivalent_fluence(
        plan["planned_fluence_per_cm2"],
        plan["niel_mev_cm2_per_g"],
        policy["reference_niel_mev_cm2_per_g"],
    )
    result["planned_equivalent_fluence_per_cm2"] = planned

    short = False
    if not _at_least(planned, required):
        short = True
        findings.append(
            "the planned exposure is worth %.4g equivalent particles per square "
            "centimetre against the %.4g the end-of-life point needs"
            % (planned, required)
        )
    if not _at_least(plan["sample_count"], policy["min_sample_count"]):
        short = True
        findings.append(
            "the plan carries %d part(s) against the %d the policy asks for; a "
            "degradation curve is not drawn through one sample"
            % (plan["sample_count"], policy["min_sample_count"])
        )

    result["verdict"] = (
        EXPOSURE_REQUIRED_PLAN_SHORT if short else EXPOSURE_REQUIRED_PLAN_ACCEPTED
    )
    return result
