#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.2.4 lightning protection requirements
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires a space system to be protected
against the direct and the indirect effects of lightning, and requires
that exposure to those effects leaves no degradation of the system's
performance. This module implements the checkable part of that clause:
categorization of a coupling mechanism as a direct or an indirect
effect, assignment of an external region to a lightning attachment
zone, the protection provisions each zone must carry, the adiabatic
conductor cross-section a stroke action integral demands, the induced
bundle transient built from the inductive and resistive coupling
terms, the decibel separation between the equipment transient design
level and that induced level, and the no-degradation check on every
function exposed to the strike. It does not synthesise a shield, does
not run a full three-dimensional field solve, and does not certify an
aircraft-style lightning test campaign.
"""

import math

# Relative tolerance that absorbs floating-point representation error
# when a quantity sits exactly on a limit. It widens no engineering
# limit: it only stops a value that is mathematically equal to the
# limit from reading as an exceedance a few ULPs out.
LIMIT_REL_TOL = 1e-9

DIRECT_EFFECT_MECHANISMS = frozenset(
    {
        "arc_root_attachment",
        "resistive_burn_through",
        "magnetic_force_pinch",
        "acoustic_shock_overpressure",
        "arc_root_metal_erosion",
    }
)
INDIRECT_EFFECT_MECHANISMS = frozenset(
    {
        "aperture_field_coupling",
        "cable_bundle_inductive_coupling",
        "structure_resistive_voltage_rise",
        "ground_potential_rise",
        "diffusion_flux_coupling",
    }
)

# External region to lightning attachment zone. Zone 1 regions take an
# initial attachment, zone 2 regions a swept stroke, the "b" variants
# additionally hold the channel for the long-duration component, and
# zone 3 conducts current without attaching.
REGION_ATTACHMENT_ZONES = {
    "nose_cap": "zone_1a",
    "fin_tip": "zone_1a",
    "forward_dome_apex": "zone_1a",
    "trailing_edge_exit_point": "zone_1b",
    "aft_skirt_exit": "zone_1b",
    "intertank_skin": "zone_2a",
    "swept_stroke_surface": "zone_2a",
    "umbilical_panel": "zone_2b",
    "protected_interior_bay": "zone_3",
    "internal_harness_raceway": "zone_3",
}

ZONE_PROTECTION_PROVISIONS = {
    "zone_1a": frozenset(
        {"conductive_attachment_path", "arc_root_thickness_margin"}
    ),
    "zone_1b": frozenset(
        {
            "conductive_attachment_path",
            "arc_root_thickness_margin",
            "hang_on_dwell_provision",
        }
    ),
    "zone_2a": frozenset(
        {"conductive_attachment_path", "diverter_or_conductive_coating"}
    ),
    "zone_2b": frozenset(
        {
            "conductive_attachment_path",
            "diverter_or_conductive_coating",
            "hang_on_dwell_provision",
        }
    ),
    "zone_3": frozenset({"current_conduction_path"}),
}

# Adiabatic action constant k, in ampere-root-second per square
# millimetre, for the conductor material carrying the stroke.
MATERIAL_ACTION_CONSTANTS_A_SQRTS_PER_MM2 = {
    "copper": 143.0,
    "aluminium": 94.0,
    "stainless_steel": 52.0,
    "titanium": 40.0,
    "meshed_carbon_composite": 25.0,
}

DEFAULT_TRANSIENT_MARGIN_DB = 6.0


def _meets_lower_limit(value, limit):
    """True when value is at or above limit, treating a value equal to
    the limit within LIMIT_REL_TOL as meeting it."""
    return value >= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def _within_upper_limit(value, limit):
    """True when value is at or below limit, treating a value equal to
    the limit within LIMIT_REL_TOL as within it."""
    return value <= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def categorize_lightning_effect(mechanism):
    """Effect family for a coupling mechanism: "direct" (the channel
    attaches to the structure) or "indirect" (the channel's field or
    potential rise couples into internal circuits). Raises ValueError
    for a mechanism outside the clause 6.3.2.4 scope."""
    if mechanism in DIRECT_EFFECT_MECHANISMS:
        return "direct"
    if mechanism in INDIRECT_EFFECT_MECHANISMS:
        return "indirect"
    raise ValueError(
        "unrecognized lightning coupling mechanism %r under "
        "E-ST-20C clause 6.3.2.4" % (mechanism,)
    )


def attachment_zone(region):
    """Lightning attachment zone for an external region. Raises
    ValueError for a region with no zone on record -- an unzoned
    external region is a finding, not a default zone 3."""
    try:
        return REGION_ATTACHMENT_ZONES[region]
    except KeyError:
        raise ValueError(
            "no lightning attachment zone on record for region %r" % (region,)
        )


def required_zone_provisions(zone):
    """Protection provisions a zone must carry. Raises ValueError for
    an unrecognized zone label."""
    try:
        return ZONE_PROTECTION_PROVISIONS[zone]
    except KeyError:
        raise ValueError("unrecognized lightning attachment zone %r" % (zone,))


def required_conductor_area_mm2(action_integral_a2s, material):
    """Adiabatic conductor cross-section, in square millimetres, that
    carries the stroke action integral without fusing: the square root
    of the action integral divided by the material action constant.
    Raises ValueError for a non-positive action integral or a material
    with no action constant on record."""
    if action_integral_a2s <= 0:
        raise ValueError("action_integral_a2s must be > 0")
    try:
        constant = MATERIAL_ACTION_CONSTANTS_A_SQRTS_PER_MM2[material]
    except KeyError:
        raise ValueError(
            "no adiabatic action constant on record for material %r"
            % (material,)
        )
    return math.sqrt(action_integral_a2s) / constant


def direct_effect_findings(region_case):
    """Findings (empty when protected) for the direct effects on one
    external region.

    region_case: {"region_id", "region", "provisions" (iterable),
    "conductor_area_mm2", "conductor_material",
    "stroke_action_integral_a2s"}. Raises ValueError through
    attachment_zone or required_conductor_area_mm2."""
    zone = attachment_zone(region_case["region"])
    findings = []
    declared = set(region_case["provisions"])
    absent = sorted(required_zone_provisions(zone) - declared)
    if absent:
        findings.append(
            {
                "region_id": region_case["region_id"],
                "issue": "missing_direct_effect_provision",
                "zone": zone,
                "missing": absent,
            }
        )
    needed = required_conductor_area_mm2(
        region_case["stroke_action_integral_a2s"],
        region_case["conductor_material"],
    )
    actual = region_case["conductor_area_mm2"]
    if actual <= 0:
        raise ValueError("conductor_area_mm2 must be > 0")
    if not _meets_lower_limit(actual, needed):
        findings.append(
            {
                "region_id": region_case["region_id"],
                "issue": "conductor_area_below_action_integral_demand",
                "zone": zone,
                "required_mm2": needed,
                "actual_mm2": actual,
            }
        )
    return findings


def inductive_transient_v(mutual_inductance_h, current_rate_a_per_s):
    """Inductively coupled open-circuit transient in volts: mutual
    inductance times the stroke current rate of rise. Raises ValueError
    for a negative inductance or a non-positive rate of rise."""
    if mutual_inductance_h < 0:
        raise ValueError("mutual_inductance_h must be >= 0")
    if current_rate_a_per_s <= 0:
        raise ValueError("current_rate_a_per_s must be > 0")
    return mutual_inductance_h * current_rate_a_per_s


def resistive_transient_v(structure_resistance_ohm, peak_current_a):
    """Resistively coupled transient in volts: the structural return
    resistance seen by the bundle times the peak stroke current. Raises
    ValueError for a negative resistance or a non-positive peak
    current."""
    if structure_resistance_ohm < 0:
        raise ValueError("structure_resistance_ohm must be >= 0")
    if peak_current_a <= 0:
        raise ValueError("peak_current_a must be > 0")
    return structure_resistance_ohm * peak_current_a


def induced_transient_level_v(bundle_case):
    """Total induced transient level in volts on one cable bundle: the
    inductive and resistive terms added directly, which is the
    conservative in-phase assumption used when the two terms' relative
    timing is not established.

    bundle_case: {"mutual_inductance_h", "current_rate_a_per_s",
    "structure_resistance_ohm", "peak_current_a"}. Raises ValueError
    through the two term functions."""
    return inductive_transient_v(
        bundle_case["mutual_inductance_h"],
        bundle_case["current_rate_a_per_s"],
    ) + resistive_transient_v(
        bundle_case["structure_resistance_ohm"],
        bundle_case["peak_current_a"],
    )


def transient_margin_db(equipment_design_level_v, induced_level_v):
    """Separation in decibels between the equipment transient design
    level and the induced transient level: twenty times the base-ten
    logarithm of their ratio. Raises ValueError for a non-positive
    level on either side."""
    if equipment_design_level_v <= 0:
        raise ValueError("equipment_design_level_v must be > 0")
    if induced_level_v <= 0:
        raise ValueError("induced_level_v must be > 0")
    return 20.0 * math.log10(equipment_design_level_v / induced_level_v)


def indirect_effect_findings(bundle_case, required_margin_db=None):
    """Findings (empty when protected) for the indirect effects on one
    cable bundle. bundle_case adds "bundle_id" and
    "equipment_design_level_v" to the induced_transient_level_v keys.
    Raises ValueError through the level and margin functions."""
    if required_margin_db is None:
        required_margin_db = DEFAULT_TRANSIENT_MARGIN_DB
    if required_margin_db < 0:
        raise ValueError("required_margin_db must be >= 0")
    induced = induced_transient_level_v(bundle_case)
    margin = transient_margin_db(
        bundle_case["equipment_design_level_v"], induced
    )
    if _meets_lower_limit(margin, required_margin_db):
        return []
    return [
        {
            "bundle_id": bundle_case["bundle_id"],
            "issue": "transient_margin_below_requirement",
            "induced_level_v": induced,
            "margin_db": margin,
            "required_margin_db": required_margin_db,
        }
    ]


def performance_degradation_findings(functions):
    """Findings (empty when no performance is degraded) across the
    functions exposed to the strike. Each entry:
    {"function_id", "parameter_deviation", "allowed_deviation",
    "self_recovering"}. Clause 6.3.2.4 asks for no degradation, so a
    deviation outside the allowed band is a finding and so is a
    deviation that needs ground intervention to clear. Raises
    ValueError for a negative allowed deviation."""
    findings = []
    for item in functions:
        allowed = item["allowed_deviation"]
        if allowed < 0:
            raise ValueError("allowed_deviation must be >= 0")
        deviation = abs(item["parameter_deviation"])
        if not _within_upper_limit(deviation, allowed):
            findings.append(
                {
                    "function_id": item["function_id"],
                    "issue": "performance_degraded_beyond_allowance",
                    "deviation": deviation,
                    "allowed_deviation": allowed,
                }
            )
        elif not item["self_recovering"]:
            findings.append(
                {
                    "function_id": item["function_id"],
                    "issue": "recovery_requires_intervention",
                    "deviation": deviation,
                }
            )
    return findings


def assess_lightning_protection(system_case, required_margin_db=None):
    """Aggregate clause 6.3.2.4 review of one space system.

    system_case: {"system_id", "regions" (list of region cases),
    "bundles" (list of bundle cases), "functions" (list of function
    records)}. Returns the three finding lists and a compliant flag
    that is true only when every list is empty. Raises ValueError
    through the per-item checks."""
    direct = []
    for region_case in system_case["regions"]:
        direct.extend(direct_effect_findings(region_case))
    indirect = []
    for bundle_case in system_case["bundles"]:
        indirect.extend(
            indirect_effect_findings(bundle_case, required_margin_db)
        )
    degradation = performance_degradation_findings(system_case["functions"])
    return {
        "system_id": system_case["system_id"],
        "direct_effect_findings": direct,
        "indirect_effect_findings": indirect,
        "performance_findings": degradation,
        "compliant": not (direct or indirect or degradation),
    }
