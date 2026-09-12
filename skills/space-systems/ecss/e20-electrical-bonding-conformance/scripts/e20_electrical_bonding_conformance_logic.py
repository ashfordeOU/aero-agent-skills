#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.8.1 electrical bonding of structure and
equipment (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the spacecraft structure and
the equipment mounted on it to be bonded in accordance with the
electromagnetic design provisions it references. This module implements
the checkable part of that clause: categorization of a bond by the
function it performs, the direct-current resistance window that
function imposes, the bulk-plus-contact model of a bond strap's
resistance, the strap inductance and length-to-width geometry rule that
govern a radio-frequency reference bond, the strap impedance at a
frequency of interest, the dissimilar-metal galvanic screen against an
environment-dependent limit, and the conductor temperature rise a fault
or surge current produces over the protection clearing time. It does
not specify surface finishes, does not size a lightning protection
network, and does not replace the bond measurement itself.
"""

import math

BOND_CATEGORY_BY_KIND = {
    "fault_current_return": "power_fault_return",
    "structure_current_return": "power_fault_return",
    "secondary_power_return": "power_fault_return",
    "rf_reference": "radio_frequency_reference",
    "shield_termination": "radio_frequency_reference",
    "antenna_ground_plane": "radio_frequency_reference",
    "lightning_down_conductor": "surge_path",
    "launcher_umbilical_bond": "surge_path",
    "equipment_mounting_face": "mechanical_interface",
    "structural_panel_joint": "mechanical_interface",
    "dielectric_surface_bleed": "electrostatic_bleed",
    "thermal_blanket_bleed": "electrostatic_bleed",
}

BOND_CATEGORIES = (
    "power_fault_return",
    "radio_frequency_reference",
    "surge_path",
    "mechanical_interface",
    "electrostatic_bleed",
)

# Acceptance window per category as (floor_ohm, ceiling_ohm). The
# conductive categories have no meaningful floor; the charge-bleed path
# has both, because a path that is too conductive defeats the isolation
# it sits beside.
BOND_RESISTANCE_WINDOW_OHM = {
    "power_fault_return": (0.0, 2.5e-3),
    "radio_frequency_reference": (0.0, 2.5e-3),
    "surge_path": (0.0, 10.0e-3),
    "mechanical_interface": (0.0, 10.0e-3),
    "electrostatic_bleed": (1.0e5, 1.0e9),
}

# Categories whose bond carries fault or surge current and therefore
# also has to survive the clearing-time energy.
CURRENT_CARRYING_CATEGORIES = frozenset(
    {"power_fault_return", "surge_path"}
)

# Classical strap geometry rule for a radio-frequency reference bond.
MAX_STRAP_LENGTH_TO_WIDTH_RATIO = 5.0
DEFAULT_RF_BOND_IMPEDANCE_LIMIT_OHM = 1.0

# Anodic index in volts; the galvanic screen works on the difference
# between the two members of the couple.
GALVANIC_ANODIC_INDEX_V = {
    "gold": 0.00,
    "rhodium_plate": 0.05,
    "silver": 0.15,
    "titanium": 0.15,
    "nickel": 0.30,
    "copper": 0.35,
    "stainless_steel_passivated": 0.50,
    "chromate_conversion_coating": 0.60,
    "tin": 0.65,
    "cadmium_plate": 0.75,
    "carbon_steel": 0.85,
    "aluminium_alloy": 0.90,
    "magnesium_alloy": 1.75,
}

# Largest allowable anodic-index difference by the environment the
# joint is exposed to across its life profile.
MAX_GALVANIC_DIFFERENCE_V = {
    "controlled": 0.50,
    "normal": 0.25,
    "harsh": 0.15,
}

DEFAULT_JOINT_COUNT = 2
DEFAULT_MAX_TEMPERATURE_RISE_K = 50.0

# Relative tolerance used to absorb floating-point representation error
# where a computed resistance, impedance, ratio or temperature rise
# lands exactly on its limit. It widens no engineering limit; it only
# stops a physically compliant equality from reading as a violation a
# few units in the last place over.
BOUNDARY_REL_TOL = 1e-9


def _exceeds(value, limit):
    """True when value is above limit by more than floating-point
    representation error. A value differing from the limit only in the
    last few bits is treated as sitting on the limit, which is
    compliant."""
    if value <= limit:
        return False
    return not math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL)


def _falls_short(value, limit):
    """True when value is below limit by more than floating-point
    representation error."""
    if value >= limit:
        return False
    return not math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL)


def categorize_bond(bond_kind):
    """Bonding function of a bond kind: "power_fault_return",
    "radio_frequency_reference", "surge_path", "mechanical_interface"
    or "electrostatic_bleed". Raises ValueError for a kind that is not
    a recognized clause 6.3.8.1 bonding function."""
    try:
        return BOND_CATEGORY_BY_KIND[bond_kind]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized bond kind %r under "
            "E-ST-20C clause 6.3.8.1" % (bond_kind,)
        )


def bond_resistance_window_ohm(category):
    """Acceptance window (floor_ohm, ceiling_ohm) for a bonding
    function. Raises ValueError for an unrecognized category."""
    try:
        return BOND_RESISTANCE_WINDOW_OHM[category]
    except (KeyError, TypeError):
        raise ValueError("unrecognized bond category %r" % (category,))


def strap_dc_resistance_ohm(
    resistivity_ohm_m,
    length_m,
    cross_section_m2,
    contact_resistance_ohm=0.0,
    joints=DEFAULT_JOINT_COUNT,
):
    """Direct-current resistance of a bond strap in ohms: the bulk term
    resistivity times length over cross-section, plus the contact
    resistance of every mechanical interface in the path. Raises
    ValueError for a negative resistivity, length or contact
    resistance, a non-positive cross-section, or a joint count that is
    not a non-negative integer."""
    if resistivity_ohm_m < 0:
        raise ValueError("resistivity_ohm_m must be >= 0")
    if length_m < 0:
        raise ValueError("length_m must be >= 0")
    if cross_section_m2 <= 0:
        raise ValueError("cross_section_m2 must be > 0")
    if contact_resistance_ohm < 0:
        raise ValueError("contact_resistance_ohm must be >= 0")
    if not isinstance(joints, int) or isinstance(joints, bool):
        raise ValueError("joints must be an integer")
    if joints < 0:
        raise ValueError("joints must be >= 0")
    bulk_ohm = resistivity_ohm_m * length_m / cross_section_m2
    return bulk_ohm + joints * contact_resistance_ohm


def strap_length_to_width_ratio(length_m, width_m):
    """Geometry ratio of a bond strap. Raises ValueError for a
    non-positive length or width."""
    if length_m <= 0:
        raise ValueError("length_m must be > 0")
    if width_m <= 0:
        raise ValueError("width_m must be > 0")
    return length_m / width_m


def strap_inductance_h(length_m, width_m):
    """Self-inductance of a flat bond strap in henry, from the standard
    thin-strap approximation: the length scaled by the logarithm of
    twice the length over the width, plus a half-turn term. Raises
    ValueError for a non-positive length or width, or for a strap
    shorter than it is wide, where the thin-strap approximation does
    not hold."""
    ratio = strap_length_to_width_ratio(length_m, width_m)
    if ratio < 1.0:
        raise ValueError(
            "thin-strap inductance model needs length_m >= width_m"
        )
    return 2.0e-7 * length_m * (math.log(2.0 * ratio) + 0.5)


def strap_impedance_ohm(resistance_ohm, inductance_h, frequency_hz):
    """Bond impedance magnitude in ohms at a frequency: the resistance
    and the strap reactance combined in quadrature. Raises ValueError
    for a negative resistance, inductance or frequency."""
    if resistance_ohm < 0:
        raise ValueError("resistance_ohm must be >= 0")
    if inductance_h < 0:
        raise ValueError("inductance_h must be >= 0")
    if frequency_hz < 0:
        raise ValueError("frequency_hz must be >= 0")
    reactance_ohm = 2.0 * math.pi * frequency_hz * inductance_h
    return math.sqrt(
        resistance_ohm * resistance_ohm + reactance_ohm * reactance_ohm
    )


def galvanic_index_difference_v(metal_a, metal_b):
    """Absolute anodic-index difference in volts between the two
    members of a bonded couple. Raises ValueError for a metal or
    finish that is not in the galvanic table."""
    for metal in (metal_a, metal_b):
        if metal not in GALVANIC_ANODIC_INDEX_V:
            raise ValueError(
                "unrecognized bonded material %r" % (metal,)
            )
    return abs(
        GALVANIC_ANODIC_INDEX_V[metal_a] - GALVANIC_ANODIC_INDEX_V[metal_b]
    )


def fault_temperature_rise_k(
    current_a, resistance_ohm, clearing_time_s, thermal_mass_j_per_k
):
    """Temperature rise in kelvin of a bond carrying a fault or surge
    current: the energy the current deposits in the bond resistance
    over the clearing time, divided by the bond's thermal mass. Raises
    ValueError for a negative current, resistance or clearing time, or
    a non-positive thermal mass."""
    if current_a < 0:
        raise ValueError("current_a must be >= 0")
    if resistance_ohm < 0:
        raise ValueError("resistance_ohm must be >= 0")
    if clearing_time_s < 0:
        raise ValueError("clearing_time_s must be >= 0")
    if thermal_mass_j_per_k <= 0:
        raise ValueError("thermal_mass_j_per_k must be > 0")
    energy_j = current_a * current_a * resistance_ohm * clearing_time_s
    return energy_j / thermal_mass_j_per_k


def resolve_bond_resistance_ohm(bond):
    """Direct-current resistance in ohms for one bond: the measured
    value when it is on record, otherwise the value computed from the
    strap geometry. Raises ValueError when neither a measurement nor a
    complete geometry is available, or through
    strap_dc_resistance_ohm for an invalid geometry."""
    measured = bond.get("measured_resistance_ohm")
    if measured is not None:
        if measured < 0:
            raise ValueError("measured_resistance_ohm must be >= 0")
        return float(measured)
    geometry = bond.get("strap")
    if not geometry:
        raise ValueError(
            "bond %r has neither a measured resistance nor a strap geometry"
            % (bond.get("bond_id"),)
        )
    return strap_dc_resistance_ohm(
        geometry["resistivity_ohm_m"],
        geometry["length_m"],
        geometry["cross_section_m2"],
        geometry.get("contact_resistance_ohm", 0.0),
        geometry.get("joints", DEFAULT_JOINT_COUNT),
    )


def resistance_findings(bond_id, category, resistance_ohm):
    """Findings (empty when inside the window) for a bond resistance
    against its category window. A charge-bleed path is reported both
    above its ceiling and below its floor. Raises ValueError for a
    negative resistance or an unrecognized category."""
    if resistance_ohm < 0:
        raise ValueError("resistance_ohm must be >= 0")
    floor_ohm, ceiling_ohm = bond_resistance_window_ohm(category)
    findings = []
    if _exceeds(resistance_ohm, ceiling_ohm):
        findings.append(
            {
                "issue": "bond_resistance_above_ceiling",
                "bond": bond_id,
                "category": category,
                "resistance_ohm": resistance_ohm,
                "ceiling_ohm": ceiling_ohm,
            }
        )
    if floor_ohm > 0 and _falls_short(resistance_ohm, floor_ohm):
        findings.append(
            {
                "issue": "bond_resistance_below_floor",
                "bond": bond_id,
                "category": category,
                "resistance_ohm": resistance_ohm,
                "floor_ohm": floor_ohm,
            }
        )
    return findings


def impedance_findings(bond_id, bond, resistance_ohm):
    """Findings (empty when acceptable) for a radio-frequency reference
    bond: the strap length-to-width ratio against the geometry rule and
    the strap impedance at the frequency of interest against the bond's
    limit. A bond without a strap geometry yields a record-style
    finding rather than a silent pass. Raises ValueError through the
    helpers for an invalid geometry or frequency."""
    geometry = bond.get("strap")
    if not geometry or "width_m" not in geometry:
        return [
            {
                "issue": "rf_bond_strap_geometry_not_on_record",
                "bond": bond_id,
            }
        ]
    findings = []
    ratio = strap_length_to_width_ratio(
        geometry["length_m"], geometry["width_m"]
    )
    if _exceeds(ratio, MAX_STRAP_LENGTH_TO_WIDTH_RATIO):
        findings.append(
            {
                "issue": "strap_length_to_width_ratio_above_limit",
                "bond": bond_id,
                "ratio": ratio,
                "limit": MAX_STRAP_LENGTH_TO_WIDTH_RATIO,
            }
        )
    inductance_h = strap_inductance_h(
        geometry["length_m"], geometry["width_m"]
    )
    impedance_ohm = strap_impedance_ohm(
        resistance_ohm, inductance_h, bond["analysis_frequency_hz"]
    )
    limit_ohm = bond.get(
        "maximum_impedance_ohm", DEFAULT_RF_BOND_IMPEDANCE_LIMIT_OHM
    )
    if limit_ohm <= 0:
        raise ValueError("maximum_impedance_ohm must be > 0")
    if _exceeds(impedance_ohm, limit_ohm):
        findings.append(
            {
                "issue": "rf_bond_impedance_above_limit",
                "bond": bond_id,
                "impedance_ohm": impedance_ohm,
                "limit_ohm": limit_ohm,
                "inductance_h": inductance_h,
            }
        )
    return findings


def galvanic_findings(bond_id, bond):
    """Findings (empty when compatible) for the dissimilar-metal couple
    of a bond, screened against the limit for the declared environment.
    Raises ValueError for an unrecognized material or environment."""
    environment = bond.get("environment", "normal")
    if environment not in MAX_GALVANIC_DIFFERENCE_V:
        raise ValueError(
            "unrecognized bonding environment %r" % (environment,)
        )
    difference_v = galvanic_index_difference_v(
        bond["material_a"], bond["material_b"]
    )
    limit_v = MAX_GALVANIC_DIFFERENCE_V[environment]
    if _exceeds(difference_v, limit_v):
        return [
            {
                "issue": "galvanic_couple_above_limit",
                "bond": bond_id,
                "environment": environment,
                "difference_v": difference_v,
                "limit_v": limit_v,
            }
        ]
    return []


def thermal_findings(bond_id, category, bond, resistance_ohm):
    """Findings (empty when acceptable) for the clearing-time heating of
    a current-carrying bond. Categories that carry no fault or surge
    current yield no findings. A current-carrying bond with no fault
    case on record yields a record-style finding. Raises ValueError
    through fault_temperature_rise_k for an invalid fault case."""
    if category not in CURRENT_CARRYING_CATEGORIES:
        return []
    fault_case = bond.get("fault_case")
    if not fault_case:
        return [
            {
                "issue": "bond_fault_case_not_on_record",
                "bond": bond_id,
                "category": category,
            }
        ]
    rise_k = fault_temperature_rise_k(
        fault_case["current_a"],
        resistance_ohm,
        fault_case["clearing_time_s"],
        fault_case["thermal_mass_j_per_k"],
    )
    limit_k = fault_case.get(
        "maximum_temperature_rise_k", DEFAULT_MAX_TEMPERATURE_RISE_K
    )
    if limit_k <= 0:
        raise ValueError("maximum_temperature_rise_k must be > 0")
    if _exceeds(rise_k, limit_k):
        return [
            {
                "issue": "bond_temperature_rise_above_limit",
                "bond": bond_id,
                "temperature_rise_k": rise_k,
                "limit_k": limit_k,
            }
        ]
    return []


def bond_review(bond):
    """Full clause 6.3.8.1 review for one bond.

    bond: {"bond_id": str, "bond_kind": str, "material_a": str,
    "material_b": str, "environment": str (optional, default
    "normal"), "measured_resistance_ohm": float or None, "strap":
    {"resistivity_ohm_m", "length_m", "cross_section_m2", "width_m"
    (radio-frequency bonds), "contact_resistance_ohm" (optional),
    "joints" (optional)}, "analysis_frequency_hz": float
    (radio-frequency bonds), "maximum_impedance_ohm": float
    (optional), "fault_case": {"current_a", "clearing_time_s",
    "thermal_mass_j_per_k", "maximum_temperature_rise_k" (optional)}}.

    Returns {"resistance": [...], "impedance": [...], "galvanic":
    [...], "thermal": [...]}. Raises ValueError through the helpers for
    an unrecognized bond kind, material or environment, or an invalid
    geometry or fault case. Does not mutate bond."""
    bond_id = bond["bond_id"]
    category = categorize_bond(bond["bond_kind"])
    resistance_ohm = resolve_bond_resistance_ohm(bond)
    impedance = (
        impedance_findings(bond_id, bond, resistance_ohm)
        if category == "radio_frequency_reference"
        else []
    )
    return {
        "resistance": resistance_findings(bond_id, category, resistance_ohm),
        "impedance": impedance,
        "galvanic": galvanic_findings(bond_id, bond),
        "thermal": thermal_findings(
            bond_id, category, bond, resistance_ohm
        ),
    }


def is_bond_compliant(review):
    """True when every finding list in a bond_review result is empty --
    the bond's resistance, impedance, galvanic couple and fault heating
    all conform to the clause 6.3.8.1 provisions."""
    return all(len(findings) == 0 for findings in review.values())
