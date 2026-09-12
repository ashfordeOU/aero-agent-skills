#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.1.3 electromagnetic interference safety
margins (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires an interference safety margin
to be determined at the critical points of the design, and requires
that determination to hold over the full range of operating conditions
rather than at one nominal point. This module implements the checkable
part of that clause: categorization of a critical point by the
consequence of the function it carries, the separation each category
demands, normalisation of a susceptibility threshold and an
interference level onto a single scale, the amplitude and power
decibel laws, the operating-condition coverage check, selection of the
governing worst case, and the aggregated per-point finding lists. It
does not measure interference, does not derive a susceptibility
threshold from a part datasheet, and does not design a filter or a
shield.
"""

import math

ORDNANCE_POINT_KINDS = frozenset(
    {
        "electro_explosive_initiator",
        "pyrotechnic_firing_line",
        "separation_bolt_drive",
        "safe_and_arm_command_line",
    }
)
SAFETY_CRITICAL_POINT_KINDS = frozenset(
    {
        "propellant_isolation_valve_drive",
        "pressurant_latch_valve_drive",
        "battery_cell_bypass_command",
        "deployment_release_actuator",
    }
)
MISSION_CRITICAL_POINT_KINDS = frozenset(
    {
        "attitude_thruster_drive",
        "reaction_wheel_torque_command",
        "star_tracker_analogue_video",
        "payload_detector_front_end",
        "bus_undervoltage_sense",
    }
)
NON_CRITICAL_POINT_KINDS = frozenset(
    {
        "housekeeping_temperature_sense",
        "status_discrete_telemetry",
        "non_critical_heater_line",
    }
)

# Separation demanded of each category, in decibels. Ordnance carries
# the widest because the failure is energetic and irreversible; a
# non-critical point only has to stay below its threshold.
REQUIRED_MARGIN_DB = {
    "ordnance": 20.0,
    "safety_critical": 12.0,
    "mission_critical": 6.0,
    "non_critical": 0.0,
}

AMPLITUDE_QUANTITIES = frozenset({"voltage", "current", "field_strength"})
POWER_QUANTITIES = frozenset({"power", "power_flux"})

MANDATORY_OPERATING_CONDITIONS = frozenset(
    {
        "all_loads_energised",
        "all_loads_de_energised",
        "transmitter_keyed",
        "mode_transition",
        "worst_case_bus_voltage",
    }
)

# Absorbs the representation error of a ratio or a difference that is
# mathematically on the requirement. It does not widen the
# requirement: it only stops a few units in the last place from being
# reported as a real shortfall.
MARGIN_TOLERANCE_DB = 1.0e-9


def categorize_critical_point(point_kind):
    """Consequence category of a critical point: "ordnance",
    "safety_critical", "mission_critical" or "non_critical". Raises
    ValueError for a kind that is not a clause 6.3.1.3 critical
    point."""
    if point_kind in ORDNANCE_POINT_KINDS:
        return "ordnance"
    if point_kind in SAFETY_CRITICAL_POINT_KINDS:
        return "safety_critical"
    if point_kind in MISSION_CRITICAL_POINT_KINDS:
        return "mission_critical"
    if point_kind in NON_CRITICAL_POINT_KINDS:
        return "non_critical"
    raise ValueError(
        "unrecognized critical point kind %r under "
        "E-ST-20C clause 6.3.1.3" % (point_kind,)
    )


def required_margin_db(category):
    """Separation in decibels demanded of a consequence category.
    Raises ValueError for a category outside the clause set."""
    if category not in REQUIRED_MARGIN_DB:
        raise ValueError("unrecognized critical point category %r" % (category,))
    return REQUIRED_MARGIN_DB[category]


def dbuv_to_volts(level_dbuv):
    """Linear volts for a level expressed in decibels above one
    microvolt. Any real input is valid: the decibel scale has no lower
    bound."""
    return (10.0 ** (level_dbuv / 20.0)) / 1.0e6


def volts_to_dbuv(level_v):
    """Level in decibels above one microvolt for a linear voltage.
    Raises ValueError for a non-positive voltage, which has no decibel
    representation."""
    if level_v <= 0:
        raise ValueError("level_v must be > 0 to express a level in dBuV")
    return 20.0 * math.log10(level_v * 1.0e6)


def amplitude_margin_db(threshold, interference):
    """Separation in decibels for an amplitude quantity (voltage,
    current, field strength): twenty times the base-ten logarithm of
    the threshold over the interference level. Raises ValueError for a
    non-positive threshold or interference level."""
    if threshold <= 0:
        raise ValueError("susceptibility threshold must be > 0 on an amplitude scale")
    if interference <= 0:
        raise ValueError("interference level must be > 0 on an amplitude scale")
    return 20.0 * math.log10(threshold / interference)


def power_margin_db(threshold_w, interference_w):
    """Separation in decibels for a power quantity: ten times the
    base-ten logarithm of the threshold over the interference level.
    Raises ValueError for a non-positive threshold or interference
    level."""
    if threshold_w <= 0:
        raise ValueError("susceptibility threshold must be > 0 on a power scale")
    if interference_w <= 0:
        raise ValueError("interference level must be > 0 on a power scale")
    return 10.0 * math.log10(threshold_w / interference_w)


def case_margin_db(case):
    """Separation in decibels for one operating-condition case.

    case: {"condition": str, "quantity": one of AMPLITUDE_QUANTITIES or
    POWER_QUANTITIES, "scale": "linear" (default) or "decibel",
    "susceptibility_threshold": float, "interference_level": float}.

    On the decibel scale the margin is the difference of the two
    levels whatever the quantity. On the linear scale an amplitude
    quantity uses the twenty-log law and a power quantity the ten-log
    law. Raises ValueError for an unrecognized quantity or scale, or
    through the margin helpers for a non-positive linear level."""
    quantity = case["quantity"]
    if quantity not in AMPLITUDE_QUANTITIES and quantity not in POWER_QUANTITIES:
        raise ValueError("unrecognized measured quantity %r" % (quantity,))
    scale = case.get("scale", "linear")
    threshold = case["susceptibility_threshold"]
    interference = case["interference_level"]
    if scale == "decibel":
        return threshold - interference
    if scale != "linear":
        raise ValueError(
            "unrecognized measurement scale %r "
            "(expected 'linear' or 'decibel')" % (scale,)
        )
    if quantity in POWER_QUANTITIES:
        return power_margin_db(threshold, interference)
    return amplitude_margin_db(threshold, interference)


def missing_operating_conditions(cases, mandatory_conditions=None):
    """Sorted list of mandatory operating conditions that no case
    exercises. mandatory_conditions defaults to
    MANDATORY_OPERATING_CONDITIONS. Raises ValueError when the
    mandatory set is empty -- a margin with no declared range of
    conditions does not satisfy the clause."""
    required = set(
        MANDATORY_OPERATING_CONDITIONS
        if mandatory_conditions is None
        else mandatory_conditions
    )
    if not required:
        raise ValueError("the mandatory operating condition set must not be empty")
    covered = {case["condition"] for case in cases}
    return sorted(required - covered)


def worst_case_margin(cases):
    """Governing case: {"condition", "margin_db"} for the smallest
    margin across cases. Ties resolve to the first case declared, so
    the result is deterministic. Raises ValueError for an empty case
    list, or through case_margin_db for a bad case."""
    if not cases:
        raise ValueError("at least one operating condition case is required")
    worst = None
    for case in cases:
        margin_db = case_margin_db(case)
        if worst is None or margin_db < worst["margin_db"]:
            worst = {"condition": case["condition"], "margin_db": margin_db}
    return worst


def margin_findings(point_id, category, cases, tolerance_db=MARGIN_TOLERANCE_DB):
    """Findings (empty when every case holds the separation) for the
    margins at one critical point. A margin that sits within
    tolerance_db of the requirement counts as on the requirement, so
    the representation error of a ratio does not become a shortfall.
    Raises ValueError for a negative tolerance, an unrecognized
    category, or through case_margin_db."""
    if tolerance_db < 0:
        raise ValueError("tolerance_db must be >= 0")
    required = required_margin_db(category)
    findings = []
    for case in cases:
        margin_db = case_margin_db(case)
        if margin_db < required and not math.isclose(
            margin_db, required, rel_tol=0.0, abs_tol=tolerance_db
        ):
            findings.append(
                {
                    "issue": "interference_safety_margin_below_requirement",
                    "point": point_id,
                    "condition": case["condition"],
                    "margin_db": margin_db,
                    "required_margin_db": required,
                }
            )
    return findings


def coverage_findings(point_id, cases, mandatory_conditions=None):
    """Findings (empty when the full range was exercised) for
    mandatory operating conditions that carry no case at this
    point."""
    return [
        {
            "issue": "operating_condition_not_exercised",
            "point": point_id,
            "condition": condition,
        }
        for condition in missing_operating_conditions(cases, mandatory_conditions)
    ]


def critical_point_review(point):
    """Full clause 6.3.1.3 review for one critical point.

    point: {"point_id": str, "point_kind": str, "cases": [case, ...],
    "mandatory_conditions": iterable (optional), "tolerance_db": float
    (optional)}.

    Returns {"coverage": [...], "margin": [...]}. Raises ValueError for
    an unrecognized point kind, an empty case list, or through the
    helpers for a bad case. Does not mutate point."""
    point_id = point["point_id"]
    category = categorize_critical_point(point["point_kind"])
    cases = point["cases"]
    if not cases:
        raise ValueError(
            "critical point %r carries no operating condition case" % (point_id,)
        )
    return {
        "coverage": coverage_findings(
            point_id, cases, point.get("mandatory_conditions")
        ),
        "margin": margin_findings(
            point_id,
            category,
            cases,
            point.get("tolerance_db", MARGIN_TOLERANCE_DB),
        ),
    }


def point_margin_summary(point):
    """Reportable summary for one critical point: its category, the
    separation demanded, the governing condition and the worst-case
    margin. Raises ValueError through the helpers for an unrecognized
    point kind, an empty case list or a bad case."""
    category = categorize_critical_point(point["point_kind"])
    worst = worst_case_margin(point["cases"])
    return {
        "point": point["point_id"],
        "category": category,
        "required_margin_db": required_margin_db(category),
        "governing_condition": worst["condition"],
        "worst_case_margin_db": worst["margin_db"],
    }


def is_point_compliant(review):
    """True when every finding list in a critical_point_review result
    is empty -- the full range of conditions was exercised and every
    one of them held the separation the category demands."""
    return all(len(findings) == 0 for findings in review.values())
