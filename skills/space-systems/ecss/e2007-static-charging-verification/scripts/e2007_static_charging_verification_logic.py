#!/usr/bin/env python3
"""Verification of the static-charging control provisions on a vehicle.

Anchor: ECSS-E-ST-20-07C clause 5.3.5 (verification of static charging
control by examination of the materials, bonding straps and blankets
provided for potential equalization). The clause is paraphrased into an
implementable procedure; no standard text is reproduced.

Model used throughout:
  materials      -> sheet resistivity places a surface in a conductive,
                    dissipative or insulating band; an insulating
                    exposed surface stores charge and is a finding
  straps         -> a strap's DC resistance is computed from geometry
                    and compared with the limit of its bonding category
  blankets       -> every layer is grounded and the ground-tab count
                    follows the blanket area against a maximum area per
                    tab, with a redundancy floor
  equalization   -> the relaxation time of a surface follows its volume
                    resistivity and permittivity and must sit under the
                    declared equalization limit

Stdlib only, deterministic, offline.
"""

import math

VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12

# --- bonding categories -----------------------------------------------------

BOND_STATIC = "category-static-equalization"
BOND_RF = "category-rf-reference"
BOND_SHOCK = "category-shock-hazard"
BOND_LIGHTNING = "category-lightning-current"

BONDING_CATEGORIES = (BOND_STATIC, BOND_RF, BOND_SHOCK, BOND_LIGHTNING)

BONDING_ALIASES = {
    "category-static-equalization": BOND_STATIC,
    "static": BOND_STATIC,
    "class-s": BOND_STATIC,
    "potential-equalization": BOND_STATIC,
    "category-rf-reference": BOND_RF,
    "rf-reference": BOND_RF,
    "class-r": BOND_RF,
    "category-shock-hazard": BOND_SHOCK,
    "shock-hazard": BOND_SHOCK,
    "class-h": BOND_SHOCK,
    "category-lightning-current": BOND_LIGHTNING,
    "lightning-current": BOND_LIGHTNING,
    "class-l": BOND_LIGHTNING,
}

# Paraphrased DC resistance ceilings, in ohms, per bonding category.
BONDING_RESISTANCE_LIMIT_OHM = {
    BOND_STATIC: 1.0,
    BOND_RF: 2.5e-3,
    BOND_SHOCK: 0.1,
    BOND_LIGHTNING: 10.0e-3,
}

# --- surface material bands -------------------------------------------------

BAND_CONDUCTIVE = "conductive"
BAND_DISSIPATIVE = "static-dissipative"
BAND_INSULATING = "insulating"

MATERIAL_BANDS = (BAND_CONDUCTIVE, BAND_DISSIPATIVE, BAND_INSULATING)

CONDUCTIVE_CEILING_OHM_PER_SQUARE = 1.0e5
DISSIPATIVE_CEILING_OHM_PER_SQUARE = 1.0e9

# An exposed external surface may not be left in the insulating band.
ACCEPTABLE_EXPOSED_BANDS = (BAND_CONDUCTIVE, BAND_DISSIPATIVE)

# --- blanket grounding ------------------------------------------------------

MIN_GROUND_TABS_PER_BLANKET = 2
DEFAULT_MAX_AREA_PER_TAB_M2 = 0.5

# --- tolerances -------------------------------------------------------------

RESISTANCE_TOLERANCE_REL = 1e-9
BAND_TOLERANCE_REL = 1e-9
AREA_TOLERANCE = 1e-9
TIME_TOLERANCE_REL = 1e-9


def _finite_number(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric" % label)
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite" % label)
    return value


def _positive(value, label):
    value = _finite_number(value, label)
    if value <= 0.0:
        raise ValueError("%s must be positive" % label)
    return value


# --- bonding categories -----------------------------------------------------


def bonding_category(raw_category):
    """Resolve a declared bonding category to its canonical name."""
    key = str(raw_category).strip().lower()
    if not key:
        raise ValueError("bonding category must not be blank")
    if key not in BONDING_ALIASES:
        raise ValueError("unrecognised bonding category: %r" % (raw_category,))
    return BONDING_ALIASES[key]


def bonding_resistance_limit_ohm(raw_category):
    """DC resistance ceiling for a bonding category."""
    return BONDING_RESISTANCE_LIMIT_OHM[bonding_category(raw_category)]


def strap_resistance_ohm(resistivity_ohm_m, length_mm, cross_section_mm2):
    """DC resistance of a bonding strap from its material and geometry."""
    resistivity = _positive(resistivity_ohm_m, "strap resistivity")
    length = _positive(length_mm, "strap length")
    area = _positive(cross_section_mm2, "strap cross section")
    return resistivity * (length * 1.0e-3) / (area * 1.0e-6)


def strap_meets_limit(resistance_ohm, raw_category, tolerance_rel=RESISTANCE_TOLERANCE_REL):
    """True when a strap resistance sits at or under its category ceiling.

    The resistance is a product and quotient of physical quantities, so
    a strap sized exactly to its ceiling can land a unit in the last
    place above it. The representation error is absorbed here; the
    ceiling itself is never relaxed.
    """
    resistance = _finite_number(resistance_ohm, "strap resistance")
    if resistance < 0.0:
        raise ValueError("strap resistance must not be negative")
    if tolerance_rel < 0.0:
        raise ValueError("tolerance must not be negative")
    limit = bonding_resistance_limit_ohm(raw_category)
    return resistance < limit or math.isclose(
        resistance, limit, rel_tol=tolerance_rel, abs_tol=0.0
    )


# --- surface materials ------------------------------------------------------


def surface_material_band(sheet_resistivity_ohm_per_square, tolerance_rel=BAND_TOLERANCE_REL):
    """Place a surface material in its resistivity band.

    The two band edges are round decades, and a material specified
    exactly at a decade must not drop into the worse band because of the
    representation of that decade, so each edge is compared with a
    relative tolerance.
    """
    value = _positive(sheet_resistivity_ohm_per_square, "sheet resistivity")
    if tolerance_rel < 0.0:
        raise ValueError("tolerance must not be negative")
    if value < CONDUCTIVE_CEILING_OHM_PER_SQUARE or math.isclose(
        value, CONDUCTIVE_CEILING_OHM_PER_SQUARE, rel_tol=tolerance_rel, abs_tol=0.0
    ):
        return BAND_CONDUCTIVE
    if value < DISSIPATIVE_CEILING_OHM_PER_SQUARE or math.isclose(
        value, DISSIPATIVE_CEILING_OHM_PER_SQUARE, rel_tol=tolerance_rel, abs_tol=0.0
    ):
        return BAND_DISSIPATIVE
    return BAND_INSULATING


def exposed_surface_is_acceptable(sheet_resistivity_ohm_per_square):
    """True when an exposed surface material cannot store static charge."""
    band = surface_material_band(sheet_resistivity_ohm_per_square)
    return band in ACCEPTABLE_EXPOSED_BANDS


def relaxation_time_s(volume_resistivity_ohm_m, relative_permittivity):
    """Charge relaxation time constant of a dielectric surface."""
    resistivity = _positive(volume_resistivity_ohm_m, "volume resistivity")
    permittivity = _finite_number(relative_permittivity, "relative permittivity")
    if permittivity < 1.0:
        raise ValueError("relative permittivity must not be below unity")
    return resistivity * permittivity * VACUUM_PERMITTIVITY_F_PER_M


def equalizes_in_time(tau_s, limit_s, tolerance_rel=TIME_TOLERANCE_REL):
    """True when a relaxation time sits at or under the equalization limit."""
    tau = _positive(tau_s, "relaxation time")
    limit = _positive(limit_s, "equalization limit")
    if tolerance_rel < 0.0:
        raise ValueError("tolerance must not be negative")
    return tau < limit or math.isclose(tau, limit, rel_tol=tolerance_rel, abs_tol=0.0)


# --- thermal blankets -------------------------------------------------------


def required_ground_tabs(area_m2, max_area_per_tab_m2=DEFAULT_MAX_AREA_PER_TAB_M2):
    """Ground tabs a blanket needs for its area, with a redundancy floor.

    The ratio is rounded up, but a blanket whose area is an exact
    multiple of the area per tab must not gain a spurious extra tab from
    the representation of that division, so the ceiling is taken on a
    value nudged down by a small absolute amount.
    """
    area = _positive(area_m2, "blanket area")
    per_tab = _positive(max_area_per_tab_m2, "maximum area per tab")
    count = int(math.ceil(area / per_tab - AREA_TOLERANCE))
    return max(count, MIN_GROUND_TABS_PER_BLANKET)


def blanket_grounding_report(blanket, max_area_per_tab_m2=DEFAULT_MAX_AREA_PER_TAB_M2):
    """Grounding verdict for one thermal blanket."""
    if not isinstance(blanket, dict):
        raise ValueError("blanket record must be a mapping")
    blanket_id = str(blanket.get("id", "")).strip()
    if not blanket_id:
        raise ValueError("blanket record must carry a non-blank id")
    area = _positive(blanket.get("area_m2"), "blanket area")
    layers = blanket.get("layer_count")
    if not isinstance(layers, int) or isinstance(layers, bool) or layers < 1:
        raise ValueError("blanket layer count must be a positive integer")
    grounded = blanket.get("grounded_layer_count")
    if not isinstance(grounded, int) or isinstance(grounded, bool) or grounded < 0:
        raise ValueError("grounded layer count must be a non-negative integer")
    if grounded > layers:
        raise ValueError("more grounded layers than layers on blanket %s" % blanket_id)
    tabs = blanket.get("ground_tab_count")
    if not isinstance(tabs, int) or isinstance(tabs, bool) or tabs < 0:
        raise ValueError("ground tab count must be a non-negative integer")
    needed = required_ground_tabs(area, max_area_per_tab_m2)
    return {
        "id": blanket_id,
        "area_m2": area,
        "layer_count": layers,
        "grounded_layer_count": grounded,
        "ground_tab_count": tabs,
        "required_ground_tabs": needed,
        "all_layers_grounded": grounded == layers,
        "tabs_sufficient": tabs >= needed,
    }


# --- top-level inspection ---------------------------------------------------


def verify_static_charging_provisions(config):
    """Run the clause 5.3.5 static-charging provision verification."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping")
    materials = config.get("materials")
    if not isinstance(materials, (list, tuple)) or not materials:
        raise ValueError("at least one surface material record is required")
    straps = config.get("straps")
    if not isinstance(straps, (list, tuple)) or not straps:
        raise ValueError("at least one bonding strap record is required")
    blankets = config.get("blankets")
    if not isinstance(blankets, (list, tuple)) or not blankets:
        raise ValueError("at least one blanket record is required")
    limit_s = _positive(config.get("equalization_limit_s", 1.0), "equalization limit")
    per_tab = _positive(
        config.get("max_area_per_tab_m2", DEFAULT_MAX_AREA_PER_TAB_M2),
        "maximum area per tab",
    )

    findings = []

    material_reports = []
    for raw in materials:
        if not isinstance(raw, dict):
            raise ValueError("material record must be a mapping")
        material_id = str(raw.get("id", "")).strip()
        if not material_id:
            raise ValueError("material record must carry a non-blank id")
        band = surface_material_band(raw.get("sheet_resistivity_ohm_per_square"))
        tau = relaxation_time_s(
            raw.get("volume_resistivity_ohm_m"),
            raw.get("relative_permittivity", 1.0),
        )
        fast_enough = equalizes_in_time(tau, limit_s)
        exposed = bool(raw.get("exposed", True))
        acceptable = (band in ACCEPTABLE_EXPOSED_BANDS) if exposed else True
        if not acceptable:
            findings.append("insulating-exposed-surface:%s" % material_id)
        if exposed and not fast_enough:
            findings.append("slow-charge-relaxation:%s" % material_id)
        material_reports.append(
            {
                "id": material_id,
                "band": band,
                "exposed": exposed,
                "relaxation_time_s": tau,
                "equalizes_in_time": fast_enough,
                "acceptable": acceptable and (fast_enough or not exposed),
            }
        )

    strap_reports = []
    for raw in straps:
        if not isinstance(raw, dict):
            raise ValueError("strap record must be a mapping")
        strap_id = str(raw.get("id", "")).strip()
        if not strap_id:
            raise ValueError("strap record must carry a non-blank id")
        category = bonding_category(raw.get("category"))
        if "resistance_ohm" in raw:
            resistance = _finite_number(raw.get("resistance_ohm"), "strap resistance")
            if resistance < 0.0:
                raise ValueError("strap resistance must not be negative")
        else:
            resistance = strap_resistance_ohm(
                raw.get("resistivity_ohm_m"),
                raw.get("length_mm"),
                raw.get("cross_section_mm2"),
            )
        ok = strap_meets_limit(resistance, category)
        if not ok:
            findings.append("bonding-strap-over-limit:%s" % strap_id)
        strap_reports.append(
            {
                "id": strap_id,
                "category": category,
                "resistance_ohm": resistance,
                "limit_ohm": bonding_resistance_limit_ohm(category),
                "meets_limit": ok,
            }
        )

    blanket_reports = []
    for raw in blankets:
        report = blanket_grounding_report(raw, per_tab)
        if not report["all_layers_grounded"]:
            findings.append("blanket-layer-not-grounded:%s" % report["id"])
        if not report["tabs_sufficient"]:
            findings.append("insufficient-ground-tabs:%s" % report["id"])
        blanket_reports.append(report)

    return {
        "equalization_limit_s": limit_s,
        "materials": tuple(material_reports),
        "straps": tuple(strap_reports),
        "blankets": tuple(blanket_reports),
        "findings": tuple(findings),
        "acceptable": not findings,
    }
