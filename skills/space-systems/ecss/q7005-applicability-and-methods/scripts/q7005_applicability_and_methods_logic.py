#!/usr/bin/env python3
"""Applicability of infrared contamination measurement, and its methods.

Anchor: ECSS-Q-ST-70-05C, the scope and applicability clauses covering
the detection of organic surface contamination by infrared
spectroscopy. The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Three questions have to be answered before a method is chosen at all.

First, whether infrared spectroscopy applies to this contaminant. It
applies to organic species with an infrared-active diagnostic band, and
only if that band falls inside the instrument's spectral range. A
contaminant that is inorganic, or whose band sits outside the range, is
outside the technique, not a difficult case for it.

Second, what is being sampled. The flight surface itself is the direct
object; a witness plate is a stand-in, and a stand-in only represents
the flight surface to the extent that its exposure time, its view of the
contamination source and its accommodation of arriving species match.
That fraction is a number, and the scaling from a witness-plate reading
to a flight-surface level is its reciprocal.

Third, which method family can reach the required cleanliness level. The
direct family reads the surface through a reflection-absorption
measurement; the indirect family extracts into a solvent and measures
the residue. Each has an areal detection limit built from different
quantities, and a family whose limit does not reach the requirement is
excluded with the reason, not quietly attempted.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DIRECT_FAMILY = "direct-ir-reflection-absorption"
INDIRECT_FAMILY = "indirect-solvent-extraction"
METHOD_FAMILIES = (DIRECT_FAMILY, INDIRECT_FAMILY)

FLIGHT_SURFACE = "flight-surface"
WITNESS_PLATE = "witness-plate"
SAMPLING_OBJECTS = (FLIGHT_SURFACE, WITNESS_PLATE)

DEFAULT_APPLICABILITY_POLICY = {
    "instrument_low_cm_1": 400.0,
    "instrument_high_cm_1": 4000.0,
    "min_represented_fraction": 0.25,
    "absorbance_detection_limit": 0.002,
    "cell_mass_detection_limit_ug": 10.0,
    "min_sampled_area_cm2": 25.0,
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


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_applicability_policy(policy):
    """Check an applicability policy carries an instrument range and limits."""
    _require_mapping("policy", policy)
    low = _require_positive("instrument_low_cm_1", policy.get("instrument_low_cm_1"))
    high = _require_positive(
        "instrument_high_cm_1", policy.get("instrument_high_cm_1")
    )
    if high <= low:
        raise ValueError(
            "instrument_high_cm_1 %g must sit above instrument_low_cm_1 %g"
            % (high, low)
        )
    _require_fraction(
        "min_represented_fraction", policy.get("min_represented_fraction")
    )
    _require_positive(
        "absorbance_detection_limit", policy.get("absorbance_detection_limit")
    )
    _require_positive(
        "cell_mass_detection_limit_ug",
        policy.get("cell_mass_detection_limit_ug"),
    )
    _require_positive(
        "min_sampled_area_cm2", policy.get("min_sampled_area_cm2")
    )
    return policy


def band_within_instrument_range(band_cm_1, policy=DEFAULT_APPLICABILITY_POLICY):
    """Whether a diagnostic band falls inside the instrument's range."""
    validate_applicability_policy(policy)
    band = _require_positive("band_cm_1", band_cm_1)
    return _at_least(band, policy["instrument_low_cm_1"]) and _at_most(
        band, policy["instrument_high_cm_1"]
    )


def screen_contaminant(contaminant, policy=DEFAULT_APPLICABILITY_POLICY):
    """Whether infrared spectroscopy is the right technique at all."""
    validate_applicability_policy(policy)
    _require_mapping("contaminant", contaminant)
    if "organic" not in contaminant:
        raise ValueError(
            "contaminant must declare whether it is organic; an unstated "
            "answer is not a no"
        )
    organic = _require_bool("contaminant organic", contaminant["organic"])
    band = _require_positive(
        "contaminant diagnostic_band_cm_1",
        contaminant.get("diagnostic_band_cm_1"),
    )
    in_range = band_within_instrument_range(band, policy)
    reasons = []
    if not organic:
        reasons.append(
            "the species is not organic, so an organic-band infrared method "
            "does not address it"
        )
    if not in_range:
        reasons.append(
            "the diagnostic band at %g cm-1 falls outside the instrument range "
            "%g to %g cm-1"
            % (band, policy["instrument_low_cm_1"], policy["instrument_high_cm_1"])
        )
    return {
        "organic": organic,
        "diagnostic_band_cm_1": band,
        "band_in_range": in_range,
        "in_scope": not reasons,
        "reasons": reasons,
    }


def witness_plate_representativeness(
    exposure_ratio, view_factor_ratio, accommodation_ratio
):
    """Fraction of the flight surface condition a witness plate stands for.

    The three ratios multiply: a plate exposed for half the time, seeing
    half the source and accommodating arriving species as well as the
    flight surface represents a quarter of it, and a reading from it is
    scaled up by the reciprocal.
    """
    exposure = _require_fraction("exposure_ratio", exposure_ratio)
    view_factor = _require_fraction("view_factor_ratio", view_factor_ratio)
    accommodation = _require_fraction("accommodation_ratio", accommodation_ratio)
    fraction = exposure * view_factor * accommodation
    return {
        "represented_fraction": fraction,
        "scale_to_flight_surface": 1.0 / fraction,
    }


def direct_method_detection_limit(
    specific_absorbance_per_ug_cm2,
    reflection_passes=1,
    policy=DEFAULT_APPLICABILITY_POLICY,
):
    """Areal contamination the direct family can just detect, in ug/cm2.

    A reflection-absorption measurement crosses the contaminant layer once
    per pass, so the absorbance detection limit divided by the specific
    absorbance and the pass count is the areal level at the limit.
    """
    validate_applicability_policy(policy)
    specific = _require_positive(
        "specific_absorbance_per_ug_cm2", specific_absorbance_per_ug_cm2
    )
    if (
        not isinstance(reflection_passes, int)
        or isinstance(reflection_passes, bool)
        or reflection_passes < 1
    ):
        raise ValueError(
            "reflection_passes must be an integer of at least 1, got %r"
            % (reflection_passes,)
        )
    return policy["absorbance_detection_limit"] / (specific * reflection_passes)


def indirect_method_detection_limit(
    sampled_area_cm2, recovery_fraction, policy=DEFAULT_APPLICABILITY_POLICY
):
    """Areal contamination the indirect family can just detect, in ug/cm2.

    The cell sees a residue mass, so the areal limit is that mass limit
    spread back over the area actually sampled and corrected for the
    fraction the extraction recovered.
    """
    validate_applicability_policy(policy)
    area = _require_positive("sampled_area_cm2", sampled_area_cm2)
    recovery = _require_fraction("recovery_fraction", recovery_fraction)
    if not _at_least(area, policy["min_sampled_area_cm2"]):
        raise ValueError(
            "sampled_area_cm2 %g is below the policy floor %g; too little area "
            "puts the residue under the cell limit by construction"
            % (area, policy["min_sampled_area_cm2"])
        )
    return policy["cell_mass_detection_limit_ug"] / (area * recovery)


def admissible_method_families(case, policy=DEFAULT_APPLICABILITY_POLICY):
    """Method families whose detection limit reaches the required level."""
    validate_applicability_policy(policy)
    _require_mapping("case", case)
    required = _require_positive(
        "required_level_ug_cm2", case.get("required_level_ug_cm2")
    )
    direct_limit = direct_method_detection_limit(
        case.get("specific_absorbance_per_ug_cm2"),
        case.get("reflection_passes", 1),
        policy,
    )
    indirect_limit = indirect_method_detection_limit(
        case.get("sampled_area_cm2"), case.get("recovery_fraction"), policy
    )
    limits = {DIRECT_FAMILY: direct_limit, INDIRECT_FAMILY: indirect_limit}
    admitted = []
    excluded = {}
    for family in METHOD_FAMILIES:
        if _at_most(limits[family], required):
            admitted.append(family)
        else:
            excluded[family] = (
                "detection limit %.4g ug/cm2 does not reach the required level "
                "%.4g ug/cm2" % (limits[family], required)
            )
    return {
        "required_level_ug_cm2": required,
        "detection_limits_ug_cm2": limits,
        "admitted": tuple(admitted),
        "excluded": excluded,
    }


def assess_applicability(case, policy=DEFAULT_APPLICABILITY_POLICY):
    """Full applicability assessment: technique, sampling object, families."""
    validate_applicability_policy(policy)
    _require_mapping("case", case)
    screening = screen_contaminant(case.get("contaminant"), policy)
    sampling_object = case.get("sampling_object")
    if sampling_object not in SAMPLING_OBJECTS:
        raise ValueError(
            "sampling_object must be one of %s, got %r"
            % (", ".join(SAMPLING_OBJECTS), sampling_object)
        )
    families = admissible_method_families(case, policy)

    representativeness = None
    findings = []
    duties = []
    if not screening["in_scope"]:
        findings.extend(screening["reasons"])
    if sampling_object == WITNESS_PLATE:
        representativeness = witness_plate_representativeness(
            case.get("exposure_ratio"),
            case.get("view_factor_ratio"),
            case.get("accommodation_ratio"),
        )
        fraction = representativeness["represented_fraction"]
        if not _at_least(fraction, policy["min_represented_fraction"]):
            findings.append(
                "the witness plate represents only %.3f of the flight surface "
                "against a required %.3f, so a reading from it cannot be scaled "
                "to a flight-surface level"
                % (fraction, policy["min_represented_fraction"])
            )
        duties.append(
            "scale the witness-plate reading to the flight surface by %.3f and "
            "state the scaling in the report, never the raw plate number"
            % representativeness["scale_to_flight_surface"]
        )
    else:
        duties.append(
            "record that the flight surface itself was sampled, so no "
            "representativeness scaling applies to the reported level"
        )
    if not families["admitted"]:
        findings.append(
            "no method family reaches the required cleanliness level of "
            "%.4g ug/cm2" % families["required_level_ug_cm2"]
        )
    duties.append(
        "state the diagnostic band the identification rests on, since a band "
        "outside the instrument range makes the whole measurement inapplicable"
    )
    return {
        "screening": screening,
        "sampling_object": sampling_object,
        "representativeness": representativeness,
        "families": families,
        "applicable": screening["in_scope"] and bool(families["admitted"]),
        "duties": duties,
        "findings": findings,
    }
