"""
Material class design rule checker — ECSS-E-ST-32C §4.5.9–§4.5.12.

Covers four structural material classes:
  METAL           — §4.5.9 ductility, SCC, galvanic compatibility
  NON_METALLIC    — §4.5.10 outgassing, radiation tolerance, temperature envelope
  COMPOSITE       — §4.5.11 layup symmetry/balance, hygrothermal knockdown, micro-cracking
  ADHESIVE_BONDED — §4.5.12 bond-line thickness, surface prep, thermal-cycle loads, peel stress

Paraphrased procedure only — not verbatim ECSS text.
Stdlib only; deterministic; offline.
"""

from __future__ import annotations

MATERIAL_CLASSES: frozenset[str] = frozenset(
    {"METAL", "NON_METALLIC", "COMPOSITE", "ADHESIVE_BONDED"}
)

# Galvanic incompatibility pairs for structural alloys (representative subset).
# An incompatible pair in direct contact without insulation or coating triggers §4.5.9.
_GALVANIC_RISK_PAIRS: frozenset[frozenset[str]] = frozenset({
    frozenset({"ALUMINIUM", "COPPER"}),
    frozenset({"MAGNESIUM", "ALUMINIUM"}),
    frozenset({"MAGNESIUM", "STEEL"}),
    frozenset({"ALUMINIUM", "STEEL"}),
    frozenset({"TITANIUM", "MAGNESIUM"}),
    frozenset({"COPPER", "STEEL"}),
})

# Outgassing limits per ECSS-Q-ST-70-02 (referenced from §4.5.10)
TML_LIMIT_PCT: float = 1.0
CVCM_LIMIT_PCT: float = 0.1

# Bond-line thickness qualified window for adhesive joints (§4.5.12)
BOND_LINE_MIN_MM: float = 0.05
BOND_LINE_MAX_MM: float = 0.50

# Minimum elongation at break for structural metals to satisfy ductility floor (§4.5.9)
ELONGATION_MIN_PCT: float = 2.0

# 0-degree ply fraction above which micro-cracking assessment is mandatory (§4.5.11)
ZERO_PLY_FRACTION_THRESHOLD: float = 0.80


def categorize_material_class(material_class: str) -> str:
    """
    Normalize and validate a material class label.

    Returns the canonical uppercase label.
    Raises ValueError if the label does not map to a recognized class.
    """
    normalized = material_class.strip().upper().replace("-", "_").replace(" ", "_")
    if normalized not in MATERIAL_CLASSES:
        raise ValueError(
            f"Unrecognized material class '{material_class}'. "
            f"Must be one of {sorted(MATERIAL_CLASSES)}."
        )
    return normalized


def check_metal_design_rules(spec: dict) -> list[str]:
    """
    Apply §4.5.9 design rules for metallic structural materials.

    Returns a list of violation strings; empty list means fully compliant.

    Required keys in spec
    ----------------------
    material_id         (str)       Alloy identifier, e.g. 'ALUMINIUM', 'STEEL'.
    yield_mpa           (float)     0.2 % proof stress (MPa).
    ultimate_mpa        (float)     Ultimate tensile strength (MPa).
    elongation_pct      (float)     Minimum elongation at break (%).
    scc_susceptible     (bool)      True when alloy is susceptible to stress-corrosion cracking.
    scc_mitigation      (bool)      True when a mitigation measure is documented.
    contact_materials   (list[str]) Alloy IDs of other materials in structural contact.
    galvanic_protection (bool)      True when insulation or protective coating is applied.
    """
    _require_keys(spec, [
        "material_id", "yield_mpa", "ultimate_mpa", "elongation_pct",
        "scc_susceptible", "scc_mitigation", "contact_materials", "galvanic_protection",
    ])
    violations: list[str] = []

    if spec["yield_mpa"] <= 0:
        violations.append("yield_mpa must be positive (§4.5.9)")
    if spec["ultimate_mpa"] <= spec["yield_mpa"]:
        violations.append("ultimate_mpa must exceed yield_mpa (§4.5.9)")
    if spec["elongation_pct"] < ELONGATION_MIN_PCT:
        violations.append(
            f"elongation {spec['elongation_pct']:.2f}% is below the "
            f"{ELONGATION_MIN_PCT:.1f}% ductility floor (§4.5.9)"
        )
    if spec["scc_susceptible"] and not spec["scc_mitigation"]:
        violations.append(
            "SCC-susceptible alloy must have a documented mitigation measure (§4.5.9)"
        )
    if not spec["galvanic_protection"]:
        base = spec["material_id"].strip().upper()
        all_alloys = {base} | {m.strip().upper() for m in spec["contact_materials"]}
        for pair in _GALVANIC_RISK_PAIRS:
            if pair.issubset(all_alloys):
                a, b = sorted(pair)
                violations.append(
                    f"Galvanic-incompatible pair {a}–{b} in direct contact without "
                    "insulation or protective coating (§4.5.9)"
                )
    return violations


def check_non_metallic_design_rules(spec: dict) -> list[str]:
    """
    Apply §4.5.10 design rules for non-metallic structural materials.

    Returns a list of violation strings; empty list means fully compliant.

    Required keys in spec
    ----------------------
    tml_pct               (float) Total mass loss from outgassing test (%).
    cvcm_pct              (float) Collected volatile condensable material (%).
    radiation_qualified   (bool)  True when radiation qualification covers the mission dose.
    temp_min_c            (float) Minimum operating temperature (°C).
    temp_max_c            (float) Maximum operating temperature (°C).
    """
    _require_keys(spec, [
        "tml_pct", "cvcm_pct", "radiation_qualified", "temp_min_c", "temp_max_c",
    ])
    violations: list[str] = []

    if spec["tml_pct"] > TML_LIMIT_PCT:
        violations.append(
            f"TML {spec['tml_pct']:.3f}% exceeds the {TML_LIMIT_PCT:.1f}% limit "
            "(§4.5.10, ECSS-Q-ST-70-02)"
        )
    if spec["cvcm_pct"] > CVCM_LIMIT_PCT:
        violations.append(
            f"CVCM {spec['cvcm_pct']:.3f}% exceeds the {CVCM_LIMIT_PCT:.2f}% limit "
            "(§4.5.10, ECSS-Q-ST-70-02)"
        )
    if not spec["radiation_qualified"]:
        violations.append(
            "Non-metallic material must be radiation-qualified to the mission dose level (§4.5.10)"
        )
    if spec["temp_max_c"] <= spec["temp_min_c"]:
        violations.append(
            f"temp_max_c ({spec['temp_max_c']}°C) must exceed "
            f"temp_min_c ({spec['temp_min_c']}°C) (§4.5.10)"
        )
    return violations


def check_composite_design_rules(spec: dict) -> list[str]:
    """
    Apply §4.5.11 design rules for composite laminate structural materials.

    Returns a list of violation strings; empty list means fully compliant.

    Required keys in spec
    ----------------------
    symmetric_layup                (bool)  True when layup is symmetric about the mid-plane.
    balanced_layup                 (bool)  True when equal +θ / −θ ply populations exist.
    hygrothermal_knockdown_applied (bool)  True when wet/hot property knockdown is in the allowables.
    min_ply_thickness_mm           (float) Nominal minimum ply thickness (mm).
    zero_ply_fraction              (float) Fraction of 0° plies in the laminate (0 to 1).
    micro_crack_assessment         (bool)  True when a micro-cracking assessment is on record.
    """
    _require_keys(spec, [
        "symmetric_layup", "balanced_layup", "hygrothermal_knockdown_applied",
        "min_ply_thickness_mm", "zero_ply_fraction", "micro_crack_assessment",
    ])
    violations: list[str] = []

    if not spec["symmetric_layup"]:
        violations.append(
            "Composite layup must be symmetric about the mid-plane to prevent "
            "bend-twist coupling under thermal and mechanical loads (§4.5.11)"
        )
    if not spec["balanced_layup"]:
        violations.append(
            "Composite layup must be balanced (+θ / −θ pairs) to prevent "
            "in-plane shear distortion under curing and thermal loads (§4.5.11)"
        )
    if not spec["hygrothermal_knockdown_applied"]:
        violations.append(
            "Hygrothermal knockdown factor (wet/hot conditions) must be present "
            "in the allowables table before strength comparison (§4.5.11)"
        )
    if spec["min_ply_thickness_mm"] <= 0:
        violations.append(
            "min_ply_thickness_mm must be positive (§4.5.11)"
        )
    if (spec["zero_ply_fraction"] > ZERO_PLY_FRACTION_THRESHOLD
            and not spec["micro_crack_assessment"]):
        pct = spec["zero_ply_fraction"] * 100
        violations.append(
            f"Laminate with {pct:.0f}% 0° plies exceeds the micro-crack susceptibility "
            f"threshold of {ZERO_PLY_FRACTION_THRESHOLD*100:.0f}%; "
            "a micro-cracking assessment under thermal cycling is required (§4.5.11)"
        )
    return violations


def check_adhesive_bonded_design_rules(spec: dict) -> list[str]:
    """
    Apply §4.5.12 design rules for adhesive-bonded structural joints.

    Returns a list of violation strings; empty list means fully compliant.

    Required keys in spec
    ----------------------
    bond_line_thickness_mm          (float) Nominal bond-line thickness (mm).
    surface_cleaned                 (bool)  True when bonding surfaces have been cleaned.
    primer_applied                  (bool)  True when bonding primer or pre-treatment is applied.
    thermal_cycling_load_considered (bool)  True when thermal-cycle-induced load is in the analysis.
    peel_stress_mpa                 (float) Calculated peel stress at the bond interface (MPa).
    peel_allowable_mpa              (float) Allowable peel stress for the adhesive system (MPa).
    """
    _require_keys(spec, [
        "bond_line_thickness_mm", "surface_cleaned", "primer_applied",
        "thermal_cycling_load_considered", "peel_stress_mpa", "peel_allowable_mpa",
    ])
    violations: list[str] = []

    t = spec["bond_line_thickness_mm"]
    if t < BOND_LINE_MIN_MM:
        violations.append(
            f"Bond-line {t:.3f} mm is below the minimum {BOND_LINE_MIN_MM} mm "
            "of the qualified adhesive window (§4.5.12)"
        )
    if t > BOND_LINE_MAX_MM:
        violations.append(
            f"Bond-line {t:.3f} mm exceeds the maximum {BOND_LINE_MAX_MM} mm "
            "of the qualified adhesive window (§4.5.12)"
        )
    if not spec["surface_cleaned"]:
        violations.append(
            "Bond surfaces must be cleaned before adhesive application (§4.5.12)"
        )
    if not spec["primer_applied"]:
        violations.append(
            "Bonding primer or pre-treatment must be applied to bond surfaces (§4.5.12)"
        )
    if not spec["thermal_cycling_load_considered"]:
        violations.append(
            "Thermal-cycling-induced peel and shear loads must be included "
            "in the joint analysis (§4.5.12)"
        )
    if spec["peel_stress_mpa"] > spec["peel_allowable_mpa"]:
        violations.append(
            f"Peel stress {spec['peel_stress_mpa']:.3f} MPa exceeds allowable "
            f"{spec['peel_allowable_mpa']:.3f} MPa (§4.5.12)"
        )
    return violations


def _require_keys(spec: dict, keys: list[str]) -> None:
    """Raise KeyError listing all missing required keys."""
    missing = [k for k in keys if k not in spec]
    if missing:
        raise KeyError(f"Spec is missing required keys: {missing}")
