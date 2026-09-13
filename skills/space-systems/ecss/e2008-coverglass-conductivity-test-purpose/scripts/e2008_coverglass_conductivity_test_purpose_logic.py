#!/usr/bin/env python3
"""Purpose of the surface conductivity survey on conductive coverglasses.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.13.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A conductive coverglass is a piece of insulating glass that has been
given a thin conductive coating on its outer face so the charge a plasma
deposits there can run sideways to a grounded point instead of sitting
still. The single number usually quoted for such a coating -- a surface
conductivity, or its reciprocal the sheet resistance -- describes one
spot. The behaviour that matters is whether the whole outer face
conducts, because charge only has to find one high-resistance island to
stop moving, and the potential that island floats to is what strikes the
discharge.

So the survey exists to answer a uniformity question, not a value
question:

    sheet resistance        the reciprocal of the surface conductivity,
                            the quantity the bleed path is sized in
    bleed time constant     how long the coated face takes to shed the
                            charge already on it
    differential potential  what a poorly conducting region floats to
                            while the plasma keeps depositing current

A survey only answers that question if its probe sites actually cover
the outer face: too few sites, sites touching too little of the area, or
a site pitch wide enough to straddle a dead patch all produce a clean
record of a coating nobody looked at.

The significance trigger and the coverage floors below are a declared
policy, not a physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Surface-charging behaviour -> the quantity the uniformity survey feeds.
SURFACE_BEHAVIOURS = {
    "array-differential-surface-charging": "coverglass-surface-potential-gradient",
    "array-electrostatic-discharge-initiation": "surface-charge-held-at-a-dead-patch",
    "array-plasma-current-collection": "coating-bleed-path-continuity",
    "array-eclipse-exit-charging-transient": "surface-charge-bleed-time-constant",
    "array-frame-potential-control": "coating-to-frame-grounding-continuity",
}

RECOGNISED_BEHAVIOURS = tuple(sorted(SURFACE_BEHAVIOURS))

COMMON_OBJECTIVE = "coverglass-outer-face-conductivity-uniformity"

UNIFORMITY_NOT_REQUIRED = "uniformity-characterisation-not-required"
SURVEY_NOT_PLANNED = "survey-not-planned"
SURVEY_INADEQUATE = "survey-inadequate"
SURFACE_UNIFORMITY_CHARACTERISED = "surface-uniformity-characterised"

DEFAULT_UNIFORMITY_POLICY = {
    "significant_potential_v": 100.0,
    "min_site_coverage_fraction": 0.02,
    "min_probe_sites": 5,
    "max_site_pitch_m": 0.030,
}

# Geometry factors for a coated face bled to a perimeter contact. They are
# shape constants of the declared model, not measured quantities.
BLEED_GEOMETRY_FACTOR = 4.0
POTENTIAL_GEOMETRY_FACTOR = 8.0

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
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


def validate_uniformity_policy(policy):
    """Check a uniformity-survey policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("significant_potential_v", policy.get("significant_potential_v"))
    coverage = _require_positive(
        "min_site_coverage_fraction", policy.get("min_site_coverage_fraction")
    )
    if coverage > 1.0:
        raise ValueError(
            "min_site_coverage_fraction %g is above one; a probe cannot touch "
            "more than the whole face" % coverage
        )
    _require_count("min_probe_sites", policy.get("min_probe_sites"))
    _require_positive("max_site_pitch_m", policy.get("max_site_pitch_m"))
    return policy


def sheet_resistance_ohm_per_square(surface_conductivity_s_per_square):
    """Sheet resistance of the coating: the reciprocal of its conductivity."""
    conductivity = _require_positive(
        "surface_conductivity_s_per_square", surface_conductivity_s_per_square
    )
    return 1.0 / conductivity


def charge_bleed_time_constant_s(
    sheet_resistance_ohm_per_sq,
    area_capacitance_f_per_m2,
    bleed_path_length_m,
    geometry_factor=BLEED_GEOMETRY_FACTOR,
):
    """How long the coated face takes to shed the charge already on it."""
    resistance = _require_positive(
        "sheet_resistance_ohm_per_sq", sheet_resistance_ohm_per_sq
    )
    capacitance = _require_positive(
        "area_capacitance_f_per_m2", area_capacitance_f_per_m2
    )
    length = _require_positive("bleed_path_length_m", bleed_path_length_m)
    factor = _require_positive("geometry_factor", geometry_factor)
    return resistance * capacitance * length * length / factor


def differential_potential_v(
    plasma_current_density_a_per_m2,
    sheet_resistance_ohm_per_sq,
    bleed_path_length_m,
    geometry_factor=POTENTIAL_GEOMETRY_FACTOR,
):
    """Potential a region floats to while the plasma keeps depositing current."""
    density = _require_non_negative(
        "plasma_current_density_a_per_m2", plasma_current_density_a_per_m2
    )
    resistance = _require_positive(
        "sheet_resistance_ohm_per_sq", sheet_resistance_ohm_per_sq
    )
    length = _require_positive("bleed_path_length_m", bleed_path_length_m)
    factor = _require_positive("geometry_factor", geometry_factor)
    return density * resistance * length * length / factor


def site_coverage_fraction(site_count, site_area_m2, coverglass_area_m2):
    """Share of the outer face the probe sites actually touch."""
    count = _require_count("site_count", site_count)
    site_area = _require_positive("site_area_m2", site_area_m2)
    face_area = _require_positive("coverglass_area_m2", coverglass_area_m2)
    touched = count * site_area
    if touched > face_area:
        raise ValueError(
            "the %d probe sites touch %g m2, more than the %g m2 outer face"
            % (count, touched, face_area)
        )
    return touched / face_area


def site_pitch_m(coverglass_area_m2, site_count):
    """Nominal spacing of an even grid of sites over the outer face."""
    face_area = _require_positive("coverglass_area_m2", coverglass_area_m2)
    count = _require_count("site_count", site_count)
    return math.sqrt(face_area / count)


def behaviour_inventory(behaviours):
    """Group the declared surface-charging behaviours, rejecting an unknown one."""
    if not isinstance(behaviours, (list, tuple, set, frozenset)):
        raise ValueError("behaviours must be a collection of behaviour names")
    grouped = []
    for behaviour in behaviours:
        if behaviour not in SURFACE_BEHAVIOURS:
            raise ValueError(
                "unknown surface-charging behaviour %r; recognised behaviours "
                "are %s" % (behaviour, ", ".join(RECOGNISED_BEHAVIOURS))
            )
        if behaviour not in grouped:
            grouped.append(behaviour)
    return tuple(sorted(grouped))


def survey_objectives(behaviours):
    """What the uniformity survey feeds, given the declared behaviours."""
    grouped = behaviour_inventory(behaviours)
    if not grouped:
        return ()
    objectives = [SURFACE_BEHAVIOURS[behaviour] for behaviour in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def assess_coverglass_conductivity_purpose(case, policy=DEFAULT_UNIFORMITY_POLICY):
    """Full clause 6.4.3.13.1 judgement for one coverglass uniformity survey."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_uniformity_policy(policy)
    if "surface_behaviours" not in case:
        raise ValueError(
            "case is missing surface_behaviours; an absent inventory is not an "
            "empty one"
        )
    behaviours = behaviour_inventory(case["surface_behaviours"])
    objectives = survey_objectives(case["surface_behaviours"])

    coverglass = case.get("coverglass")
    if not isinstance(coverglass, dict):
        raise ValueError("case is missing a coverglass block")
    sheet_resistance = sheet_resistance_ohm_per_square(
        coverglass.get("surface_conductivity_s_per_square")
    )
    face_area = _require_positive("coverglass area_m2", coverglass.get("area_m2"))
    bleed_length = _require_positive(
        "coverglass bleed_path_length_m", coverglass.get("bleed_path_length_m")
    )
    potential = differential_potential_v(
        coverglass.get("plasma_current_density_a_per_m2"),
        sheet_resistance,
        bleed_length,
    )
    bleed_time = charge_bleed_time_constant_s(
        sheet_resistance,
        coverglass.get("area_capacitance_f_per_m2"),
        bleed_length,
    )

    trigger = float(policy["significant_potential_v"])
    significant = _at_least(potential, trigger)
    findings = []
    result = {
        "surface_behaviours": behaviours,
        "objectives": objectives,
        "sheet_resistance_ohm_per_sq": sheet_resistance,
        "differential_potential_v": potential,
        "charge_bleed_time_constant_s": bleed_time,
        "significant_potential_v": trigger,
        "site_coverage_fraction": None,
        "site_pitch_m": None,
        "coverage_adequate": None,
        "site_count_adequate": None,
        "pitch_adequate": None,
        "findings": findings,
    }

    if not (behaviours and significant):
        if not behaviours:
            findings.append(
                "no surface-charging behaviour is declared for the coating "
                "uniformity to be characterised against"
            )
        if not significant:
            findings.append(
                "a poorly conducting region would float to %.4g V, below the "
                "%.4g V that makes the survey worth running"
                % (potential, trigger)
            )
        result["required"] = False
        result["verdict"] = UNIFORMITY_NOT_REQUIRED
        return result

    result["required"] = True
    survey = case.get("survey")
    if survey is None:
        findings.append(
            "the uniformity characterisation is required but no probe survey "
            "is planned; the purpose is stated and not yet served"
        )
        result["verdict"] = SURVEY_NOT_PLANNED
        return result
    if not isinstance(survey, dict):
        raise ValueError("survey must be a mapping, got %r" % (survey,))

    site_count = _require_count("survey site_count", survey.get("site_count"))
    coverage = site_coverage_fraction(
        site_count, survey.get("site_area_m2"), face_area
    )
    pitch = site_pitch_m(face_area, site_count)

    coverage_floor = float(policy["min_site_coverage_fraction"])
    coverage_ok = _at_least(coverage, coverage_floor)
    count_ok = site_count >= int(policy["min_probe_sites"])
    pitch_ok = _at_most(pitch, float(policy["max_site_pitch_m"]))

    result["site_coverage_fraction"] = coverage
    result["site_pitch_m"] = pitch
    result["coverage_adequate"] = coverage_ok
    result["site_count_adequate"] = count_ok
    result["pitch_adequate"] = pitch_ok

    if not coverage_ok:
        findings.append(
            "the probe sites touch %.4g of the outer face, below the %.4g the "
            "survey policy asks for" % (coverage, coverage_floor)
        )
    if not count_ok:
        findings.append(
            "%d probe sites is fewer than the %d the survey policy asks for"
            % (site_count, int(policy["min_probe_sites"]))
        )
    if not pitch_ok:
        findings.append(
            "a %.4g m site pitch can straddle a dead patch; the policy pitch "
            "ceiling is %.4g m" % (pitch, float(policy["max_site_pitch_m"]))
        )

    result["verdict"] = (
        SURFACE_UNIFORMITY_CHARACTERISED
        if coverage_ok and count_ok and pitch_ok
        else SURVEY_INADEQUATE
    )
    return result
