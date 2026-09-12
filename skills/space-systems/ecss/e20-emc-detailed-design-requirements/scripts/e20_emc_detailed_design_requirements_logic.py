#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.9 detailed electromagnetic compatibility
design requirements (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the detailed electromagnetic
compatibility design of the spacecraft and its equipment to be carried
out following the electromagnetic design clause it refers to. This
module implements the checkable part of that clause: the mapping of a
requirement kind onto exactly one electromagnetic family, the
interpolation of an emission limit line in decibels against the
base-ten logarithm of frequency with refusal outside the covered range,
the incoherent power sum of the conducted emission of several units on
a shared bus, the electromagnetic safety margin between a
susceptibility threshold and the environment level against the margin a
function criticality demands, and the shielding effectiveness an
enclosure owes. It does not run a test, does not synthesise a filter
and does not model an enclosure aperture.
"""

import math

# Relative tolerance used only to absorb floating-point representation
# error on an exactly-at-the-limit comparison, and an absolute
# companion for decibel quantities, which are differences and can sit
# legitimately at zero. Neither widens an engineering limit.
LIMIT_REL_TOL = 1e-9
LIMIT_ABS_TOL_DB = 1e-9

FAMILY_BY_REQUIREMENT_KIND = {
    "conducted_emission_power_leads": "conducted_emission",
    "conducted_emission_common_mode": "conducted_emission",
    "conducted_emission_inrush": "conducted_emission",
    "conducted_susceptibility_bus_ripple": "conducted_susceptibility",
    "conducted_susceptibility_transient": "conducted_susceptibility",
    "conducted_susceptibility_common_mode": "conducted_susceptibility",
    "radiated_emission_electric_field": "radiated_emission",
    "radiated_emission_magnetic_field": "radiated_emission",
    "radiated_susceptibility_electric_field": "radiated_susceptibility",
    "radiated_susceptibility_magnetic_field": "radiated_susceptibility",
    "electrostatic_discharge_immunity": "esd_immunity",
}

EMISSION_FAMILIES = frozenset({"conducted_emission", "radiated_emission"})
SUSCEPTIBILITY_FAMILIES = frozenset(
    {"conducted_susceptibility", "radiated_susceptibility", "esd_immunity"}
)

# Electromagnetic safety margin in decibels demanded by the criticality
# of the function the requirement protects.
SAFETY_MARGIN_DB_BY_CRITICALITY = {
    "standard": 6.0,
    "mission_critical": 12.0,
    "safety_critical": 20.0,
}


def categorize_emc_requirement(requirement_kind):
    """Electromagnetic family for a clause 6.3.9 requirement kind.
    Raises ValueError for a kind that belongs to no family."""
    try:
        return FAMILY_BY_REQUIREMENT_KIND[requirement_kind]
    except (KeyError, TypeError):
        raise ValueError(
            "uncategorized requirement kind %r under E-ST-20C clause 6.3.9"
            % (requirement_kind,)
        )


def is_susceptibility_family(family):
    """True for a family judged by a margin above the environment,
    False for one judged against a limit line. Raises ValueError for a
    family outside the recognised set."""
    if family in SUSCEPTIBILITY_FAMILIES:
        return True
    if family in EMISSION_FAMILIES:
        return False
    raise ValueError("unrecognized electromagnetic family %r" % (family,))


def required_safety_margin_db(family, criticality):
    """Electromagnetic safety margin in decibels the function
    criticality demands. Raises ValueError for an unrecognized
    criticality, and for an emission family, which is judged against a
    limit line rather than a margin."""
    if not is_susceptibility_family(family):
        raise ValueError(
            "family %r is judged against a limit line, not a safety margin"
            % (family,)
        )
    try:
        return SAFETY_MARGIN_DB_BY_CRITICALITY[criticality]
    except (KeyError, TypeError):
        raise ValueError("unrecognized criticality %r" % (criticality,))


def validate_limit_line(limit_points):
    """Return the limit line as a list of (frequency, level) pairs after
    checking it is usable: at least two break points, every frequency
    positive, and frequencies strictly increasing. Raises ValueError
    otherwise."""
    points = list(limit_points)
    if len(points) < 2:
        raise ValueError("limit line needs at least two break points")
    previous_f = None
    for frequency_hz, _level_dbuv in points:
        if frequency_hz <= 0:
            raise ValueError("limit line frequencies must be > 0")
        if previous_f is not None and frequency_hz <= previous_f:
            raise ValueError(
                "limit line frequencies must be strictly increasing"
            )
        previous_f = frequency_hz
    return points


def limit_level_dbuv(limit_points, frequency_hz):
    """Applicable limit level in decibels at a frequency, interpolated
    linearly in decibels against the base-ten logarithm of frequency.
    Raises ValueError for a frequency outside the range the line covers
    -- the line is not extrapolated -- or through validate_limit_line."""
    points = validate_limit_line(limit_points)
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be > 0")
    low_f, low_level = points[0]
    high_f, high_level = points[-1]
    if frequency_hz < low_f or frequency_hz > high_f:
        raise ValueError(
            "frequency %r is outside the limit line range [%r, %r]"
            % (frequency_hz, low_f, high_f)
        )
    for index in range(len(points) - 1):
        f_a, level_a = points[index]
        f_b, level_b = points[index + 1]
        if f_a <= frequency_hz <= f_b:
            if frequency_hz == f_a:
                return level_a
            if frequency_hz == f_b:
                return level_b
            span = math.log10(f_b) - math.log10(f_a)
            fraction = (math.log10(frequency_hz) - math.log10(f_a)) / span
            return level_a + fraction * (level_b - level_a)
    return high_level


def emission_findings(emission):
    """Findings (empty when compliant) for one emission measurement.

    emission: {"requirement_id": str, "requirement_kind": str,
    "frequency_hz": float, "measured_dbuv": float, "limit_points":
    [(frequency_hz, level_dbuv), ...]}. A measured level landing
    exactly on the interpolated limit is compliant. Raises ValueError
    for a susceptibility family, which has no limit line here, or
    through limit_level_dbuv."""
    family = categorize_emc_requirement(emission["requirement_kind"])
    if is_susceptibility_family(family):
        raise ValueError(
            "requirement %r is a susceptibility family; use "
            "susceptibility_findings" % (emission["requirement_kind"],)
        )
    limit_dbuv = limit_level_dbuv(
        emission["limit_points"], emission["frequency_hz"]
    )
    measured_dbuv = emission["measured_dbuv"]
    if measured_dbuv <= limit_dbuv or math.isclose(
        measured_dbuv,
        limit_dbuv,
        rel_tol=LIMIT_REL_TOL,
        abs_tol=LIMIT_ABS_TOL_DB,
    ):
        return []
    return [
        {
            "issue": "emission_level_above_limit_line",
            "requirement": emission["requirement_id"],
            "family": family,
            "frequency_hz": emission["frequency_hz"],
            "measured_dbuv": measured_dbuv,
            "limit_dbuv": limit_dbuv,
        }
    ]


def power_sum_dbuv(levels_dbuv):
    """Incoherent sum of several decibel levels: convert out of
    decibels, add the powers, convert back. Two equal contributors cost
    about three decibels. Raises ValueError for an empty sequence."""
    levels = list(levels_dbuv)
    if not levels:
        raise ValueError("levels_dbuv must not be empty")
    total = 0.0
    for level_dbuv in levels:
        total += 10.0 ** (level_dbuv / 10.0)
    if total <= 0:
        raise ValueError("power sum must be > 0")
    return 10.0 * math.log10(total)


def bus_emission_findings(bus_id, unit_levels_dbuv, bus_limit_dbuv):
    """Findings (empty when compliant) for the conducted emission of the
    units sharing one power bus. The aggregate landing exactly on the
    bus limit is compliant. Raises ValueError through power_sum_dbuv
    for an empty unit list."""
    aggregate_dbuv = power_sum_dbuv(unit_levels_dbuv)
    if aggregate_dbuv <= bus_limit_dbuv or math.isclose(
        aggregate_dbuv,
        bus_limit_dbuv,
        rel_tol=LIMIT_REL_TOL,
        abs_tol=LIMIT_ABS_TOL_DB,
    ):
        return []
    return [
        {
            "issue": "aggregated_bus_emission_above_limit",
            "bus": bus_id,
            "aggregate_dbuv": aggregate_dbuv,
            "limit_dbuv": bus_limit_dbuv,
            "unit_count": len(list(unit_levels_dbuv)),
        }
    ]


def emc_safety_margin_db(susceptibility_threshold_dbuv, environment_level_dbuv):
    """Electromagnetic safety margin in decibels: how far the
    susceptibility threshold sits above the environment the unit
    actually operates in. Negative means the environment already
    exceeds the threshold. Raises ValueError for a non-numeric level."""
    for name, value in (
        ("susceptibility_threshold_dbuv", susceptibility_threshold_dbuv),
        ("environment_level_dbuv", environment_level_dbuv),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a number" % name)
        if math.isnan(value) or math.isinf(value):
            raise ValueError("%s must be finite" % name)
    return susceptibility_threshold_dbuv - environment_level_dbuv


def susceptibility_findings(requirement):
    """Findings (empty when compliant) for one susceptibility
    requirement.

    requirement: {"requirement_id": str, "requirement_kind": str,
    "threshold_dbuv": float, "environment_dbuv": float, "criticality":
    str}. A margin landing exactly on the demanded value is compliant.
    Raises ValueError for an emission family, an unrecognized
    criticality, or through emc_safety_margin_db."""
    family = categorize_emc_requirement(requirement["requirement_kind"])
    if not is_susceptibility_family(family):
        raise ValueError(
            "requirement %r is an emission family; use emission_findings"
            % (requirement["requirement_kind"],)
        )
    demanded_db = required_safety_margin_db(
        family, requirement["criticality"]
    )
    margin_db = emc_safety_margin_db(
        requirement["threshold_dbuv"], requirement["environment_dbuv"]
    )
    if margin_db >= demanded_db or math.isclose(
        margin_db, demanded_db, rel_tol=LIMIT_REL_TOL, abs_tol=LIMIT_ABS_TOL_DB
    ):
        return []
    return [
        {
            "issue": "emc_safety_margin_below_demanded",
            "requirement": requirement["requirement_id"],
            "family": family,
            "margin_db": margin_db,
            "demanded_db": demanded_db,
            "criticality": requirement["criticality"],
        }
    ]


def required_shielding_effectiveness_db(
    external_field_dbuvm, internal_allowable_dbuvm
):
    """Shielding effectiveness in decibels an enclosure owes: the
    external field level less the internal allowable level, floored at
    zero when the environment already sits below the allowable. Raises
    ValueError for a non-finite level."""
    for name, value in (
        ("external_field_dbuvm", external_field_dbuvm),
        ("internal_allowable_dbuvm", internal_allowable_dbuvm),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a number" % name)
        if math.isnan(value) or math.isinf(value):
            raise ValueError("%s must be finite" % name)
    difference_db = external_field_dbuvm - internal_allowable_dbuvm
    if difference_db <= 0:
        return 0.0
    return difference_db


def shielding_findings(enclosure):
    """Findings (empty when compliant) for one enclosure.

    enclosure: {"enclosure_id": str, "external_field_dbuvm": float,
    "internal_allowable_dbuvm": float, "achieved_effectiveness_db":
    float}. An achieved effectiveness landing exactly on the required
    value is compliant. Raises ValueError for a negative achieved
    effectiveness or through required_shielding_effectiveness_db."""
    achieved_db = enclosure["achieved_effectiveness_db"]
    if achieved_db < 0:
        raise ValueError("achieved_effectiveness_db must be >= 0")
    required_db = required_shielding_effectiveness_db(
        enclosure["external_field_dbuvm"],
        enclosure["internal_allowable_dbuvm"],
    )
    if achieved_db >= required_db or math.isclose(
        achieved_db, required_db, rel_tol=LIMIT_REL_TOL, abs_tol=LIMIT_ABS_TOL_DB
    ):
        return []
    return [
        {
            "issue": "shielding_effectiveness_below_required",
            "enclosure": enclosure["enclosure_id"],
            "achieved_db": achieved_db,
            "required_db": required_db,
        }
    ]


def emc_design_review(design):
    """Full clause 6.3.9 review of one detailed electromagnetic design.

    design: {"requirement_kinds": [str], "emissions":
    [...see emission_findings...], "buses": [{"bus_id",
    "unit_levels_dbuv", "bus_limit_dbuv"}], "susceptibilities":
    [...see susceptibility_findings...], "enclosures":
    [...see shielding_findings...]}.

    Returns {"family": [...], "emission": [...], "bus": [...],
    "susceptibility": [...], "shielding": [...]}. The family list
    records every declared requirement kind that belongs to no family,
    reported rather than raised so the whole design can be reviewed in
    one pass; every other helper still raises on bad input. Does not
    mutate design."""
    family_findings = []
    for requirement_kind in design.get("requirement_kinds", []):
        try:
            categorize_emc_requirement(requirement_kind)
        except ValueError:
            family_findings.append(
                {
                    "issue": "requirement_kind_in_no_emc_family",
                    "requirement_kind": requirement_kind,
                }
            )
    emission = []
    for item in design.get("emissions", []):
        emission.extend(emission_findings(item))
    bus = []
    for item in design.get("buses", []):
        bus.extend(
            bus_emission_findings(
                item["bus_id"],
                item["unit_levels_dbuv"],
                item["bus_limit_dbuv"],
            )
        )
    susceptibility = []
    for item in design.get("susceptibilities", []):
        susceptibility.extend(susceptibility_findings(item))
    shielding = []
    for item in design.get("enclosures", []):
        shielding.extend(shielding_findings(item))
    return {
        "family": family_findings,
        "emission": emission,
        "bus": bus,
        "susceptibility": susceptibility,
        "shielding": shielding,
    }


def is_emc_design_compliant(review):
    """True when every finding list in an emc_design_review result is
    empty -- every requirement is categorized, every emission sits
    under its limit line, the shared buses sit under theirs, every
    susceptibility threshold holds its demanded margin and every
    enclosure delivers the effectiveness it owes."""
    return all(len(findings) == 0 for findings in review.values())
