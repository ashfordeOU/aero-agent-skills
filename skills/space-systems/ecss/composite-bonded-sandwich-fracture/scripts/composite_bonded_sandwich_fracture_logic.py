"""
Composite/bonded/sandwich fracture assessment logic.
Implements defect categorization, mixed-mode delamination growth driving
force, flaw-size allowable check, and residual strength margin per
ECSS-E-ST-32C clause 8.4 (paraphrased procedure — no verbatim ECSS text).
stdlib only — no third-party dependencies.
"""

import math
from typing import NamedTuple, List, Tuple, Optional

# ---------------------------------------------------------------------------
# Taxonomy constants
# ---------------------------------------------------------------------------

DEFECT_TYPES = frozenset({
    "delamination",
    "disbond",
    "core_damage",
    "matrix_crack",
    "impact_damage",
})

DEFECT_LOCATIONS = frozenset({
    "inner_facesheet",
    "outer_facesheet",
    "core",
    "facesheet_core_interface",
    "mid_laminate",
})

THREAT_CATEGORIES = frozenset({
    "tool_drop",
    "handling_impact",
    "debris_impact",
    "manufacturing_void",
    "porosity",
    "bird_strike",
    "hail",
})

REQUIRED_THREAT_CATEGORIES = frozenset({
    "tool_drop",
    "handling_impact",
    "debris_impact",
    "manufacturing_void",
})


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class DefectRecord(NamedTuple):
    defect_id: str
    defect_type: str
    location: str
    measured_area_mm2: float


class LoadCase(NamedTuple):
    load_case_id: str
    applied_stress_MPa: float
    G_I_Jm2: float
    G_II_Jm2: float


class MaterialAllowables(NamedTuple):
    G_Ic_Jm2: float
    G_IIc_Jm2: float
    K_Ic_MPa_sqrtm: float
    sigma_allowable_MPa: float


class PanelInput(NamedTuple):
    panel_id: str
    allowable_flaw_area_mm2: float
    allowable_crack_half_length_mm: float
    material: MaterialAllowables
    defects: List[DefectRecord]
    load_cases: List[LoadCase]
    threat_sources: List[str]


class FindingRecord(NamedTuple):
    finding_id: str
    severity: str
    description: str


# ---------------------------------------------------------------------------
# Core engineering functions
# ---------------------------------------------------------------------------

def categorize_defect(defect_type: str, location: str) -> dict:
    """
    Categorize a detected defect by structural group and laminate zone.

    Returns a dict with keys 'category', 'type', and 'location_zone'.
    Raises ValueError for any unrecognized type or location — callers must
    not assume a default category when the input is ambiguous.
    """
    if defect_type not in DEFECT_TYPES:
        raise ValueError(
            f"Unrecognized defect type '{defect_type}'. "
            f"Expected one of: {sorted(DEFECT_TYPES)}"
        )
    if location not in DEFECT_LOCATIONS:
        raise ValueError(
            f"Unrecognized defect location '{location}'. "
            f"Expected one of: {sorted(DEFECT_LOCATIONS)}"
        )

    if defect_type in {"delamination", "matrix_crack"}:
        category = "interlaminar"
    elif defect_type in {"disbond", "core_damage"}:
        category = "sandwich_interface"
    else:
        category = "impact_induced"

    return {"category": category, "type": defect_type, "location_zone": location}


def compute_mixed_mode_driving_force(
    G_I_Jm2: float,
    G_II_Jm2: float,
    G_Ic_Jm2: float,
    G_IIc_Jm2: float,
    exponent_m: float = 1.0,
    exponent_n: float = 1.0,
) -> float:
    """
    Compute the mixed-mode delamination growth driving force D.

    Power-law interaction criterion (ECSS-E-ST-32C clause 8.4 paraphrase):
        D = (G_I / G_Ic)^m + (G_II / G_IIc)^n

    D >= 1.0 indicates onset of delamination growth.
    Raises ValueError for non-positive critical SERRs or negative applied SERRs.
    """
    if G_Ic_Jm2 <= 0.0:
        raise ValueError(f"G_Ic must be positive; got {G_Ic_Jm2}.")
    if G_IIc_Jm2 <= 0.0:
        raise ValueError(f"G_IIc must be positive; got {G_IIc_Jm2}.")
    if G_I_Jm2 < 0.0:
        raise ValueError(f"G_I cannot be negative; got {G_I_Jm2}.")
    if G_II_Jm2 < 0.0:
        raise ValueError(f"G_II cannot be negative; got {G_II_Jm2}.")

    return (G_I_Jm2 / G_Ic_Jm2) ** exponent_m + (G_II_Jm2 / G_IIc_Jm2) ** exponent_n


def compute_growth_margin(driving_force: float) -> float:
    """
    Compute the delamination growth margin: margin = 1/D - 1.

    A positive margin means growth does not initiate; zero or negative means
    onset or active propagation.
    Raises ValueError if driving_force is not strictly positive.
    """
    if driving_force <= 0.0:
        raise ValueError(f"Driving force must be positive; got {driving_force}.")
    return (1.0 / driving_force) - 1.0


def check_flaw_within_allowable(
    measured_area_mm2: float,
    allowable_area_mm2: float,
) -> Tuple[bool, float]:
    """
    Check whether the measured flaw area is within the allowable flaw area.

    Returns (within_allowable, margin_fraction) where
    margin_fraction = (allowable - measured) / allowable.
    A negative margin_fraction means the flaw exceeds the allowable.
    Raises ValueError for non-positive allowable or negative measured area.
    """
    if allowable_area_mm2 <= 0.0:
        raise ValueError(f"Allowable flaw area must be positive; got {allowable_area_mm2}.")
    if measured_area_mm2 < 0.0:
        raise ValueError(f"Measured flaw area cannot be negative; got {measured_area_mm2}.")
    margin = (allowable_area_mm2 - measured_area_mm2) / allowable_area_mm2
    return measured_area_mm2 <= allowable_area_mm2, margin


def compute_residual_strength_margin(
    K_Ic_MPa_sqrtm: float,
    applied_stress_MPa: float,
    crack_half_length_mm: float,
    geometry_factor: float = 1.0,
) -> float:
    """
    Compute the residual strength margin using linear elastic fracture mechanics.

    For a through crack: K_I = geometry_factor * sigma * sqrt(pi * a).
    Margin = K_Ic / K_I - 1.
    Zero applied stress returns +inf (no fracture driving force).
    Raises ValueError for non-positive K_Ic, crack length, or geometry factor,
    and for a negative applied stress.
    """
    if K_Ic_MPa_sqrtm <= 0.0:
        raise ValueError(f"K_Ic must be positive; got {K_Ic_MPa_sqrtm}.")
    if applied_stress_MPa < 0.0:
        raise ValueError(f"Applied stress cannot be negative; got {applied_stress_MPa}.")
    if crack_half_length_mm <= 0.0:
        raise ValueError(f"Crack half-length must be positive; got {crack_half_length_mm}.")
    if geometry_factor <= 0.0:
        raise ValueError(f"Geometry factor must be positive; got {geometry_factor}.")

    if applied_stress_MPa == 0.0:
        return float("inf")

    a_m = crack_half_length_mm / 1000.0
    K_I = geometry_factor * applied_stress_MPa * math.sqrt(math.pi * a_m)
    return K_Ic_MPa_sqrtm / K_I - 1.0


def assess_damage_threat_coverage(
    threat_sources: List[str],
    required: Optional[frozenset] = None,
) -> Tuple[bool, List[str]]:
    """
    Verify the damage-threat matrix covers all required source categories.

    Returns (all_covered, missing) where missing is a sorted list of required
    categories absent from threat_sources.
    Raises ValueError for any unrecognized source string.
    """
    if required is None:
        required = REQUIRED_THREAT_CATEGORIES

    for src in threat_sources:
        if src not in THREAT_CATEGORIES:
            raise ValueError(
                f"Unrecognized threat source '{src}'. "
                f"Expected one of: {sorted(THREAT_CATEGORIES)}"
            )

    missing = sorted(required - set(threat_sources))
    return len(missing) == 0, missing


# ---------------------------------------------------------------------------
# Panel-level assessment orchestrator
# ---------------------------------------------------------------------------

def run_panel_assessment(panel: PanelInput) -> Tuple[bool, List[FindingRecord]]:
    """
    Run the full composite/bonded/sandwich fracture assessment for one panel.

    Steps:
    1. Categorize each defect; flag unrecognized types as FAIL.
    2. Check each flaw against the panel's flaw-size allowable.
    3. Compute the mixed-mode growth driving force for each defect × load case.
    4. Compute residual strength margin for each load case at the allowable
       crack half-length.
    5. Check damage-threat source coverage.

    Returns (compliant, findings). The panel is compliant only when
    the FAIL list is empty.
    """
    findings: List[FindingRecord] = []
    counter = [0]

    def record(severity: str, description: str) -> None:
        counter[0] += 1
        findings.append(FindingRecord(f"F{counter[0]:03d}", severity, description))

    for defect in panel.defects:
        # Step 1: categorize
        try:
            cat = categorize_defect(defect.defect_type, defect.location)
        except ValueError as exc:
            record("FAIL", f"Defect {defect.defect_id}: {exc}")
            continue

        # Step 2: flaw-size allowable
        try:
            within, margin = check_flaw_within_allowable(
                defect.measured_area_mm2,
                panel.allowable_flaw_area_mm2,
            )
        except ValueError as exc:
            record("FAIL", f"Defect {defect.defect_id}: flaw-size input error — {exc}")
            continue

        if not within:
            record(
                "FAIL",
                f"Defect {defect.defect_id} ({cat['category']} at "
                f"{defect.location}): measured area {defect.measured_area_mm2:.1f} mm² "
                f"exceeds allowable {panel.allowable_flaw_area_mm2:.1f} mm² "
                f"(margin {margin * 100:.1f}%).",
            )
        elif margin < 0.10:
            record(
                "WARN",
                f"Defect {defect.defect_id}: flaw area within allowable but margin "
                f"is only {margin * 100:.1f}% (< 10 % advisory threshold).",
            )

        # Step 3: delamination growth for each load case
        for lc in panel.load_cases:
            try:
                D = compute_mixed_mode_driving_force(
                    lc.G_I_Jm2,
                    lc.G_II_Jm2,
                    panel.material.G_Ic_Jm2,
                    panel.material.G_IIc_Jm2,
                )
            except ValueError as exc:
                record(
                    "FAIL",
                    f"Defect {defect.defect_id}, load case {lc.load_case_id}: "
                    f"SERR input error — {exc}",
                )
                continue

            gm = compute_growth_margin(D)
            if gm < 0.0:
                record(
                    "FAIL",
                    f"Defect {defect.defect_id}, load case {lc.load_case_id}: "
                    f"delamination growth onset predicted (D={D:.3f}, "
                    f"margin={gm * 100:.1f}%).",
                )
            elif gm < 0.15:
                record(
                    "WARN",
                    f"Defect {defect.defect_id}, load case {lc.load_case_id}: "
                    f"growth margin {gm * 100:.1f}% < 15 % advisory.",
                )

    # Step 4: residual strength for each load case
    for lc in panel.load_cases:
        try:
            rsm = compute_residual_strength_margin(
                panel.material.K_Ic_MPa_sqrtm,
                lc.applied_stress_MPa,
                panel.allowable_crack_half_length_mm,
            )
        except ValueError as exc:
            record(
                "FAIL",
                f"Load case {lc.load_case_id}: residual strength input error — {exc}",
            )
            continue

        if rsm < 0.0:
            record(
                "FAIL",
                f"Load case {lc.load_case_id}: residual strength exhausted "
                f"(margin={rsm * 100:.1f}%).",
            )

    # Step 5: damage-threat coverage
    try:
        covered, missing = assess_damage_threat_coverage(panel.threat_sources)
    except ValueError as exc:
        record("FAIL", f"Damage-threat matrix input error — {exc}")
        covered = False
        missing = []

    if not covered:
        record(
            "FAIL",
            f"Damage-threat matrix missing required source categories: {missing}. "
            f"All required categories must appear before fracture compliance is declared.",
        )

    fail_count = sum(1 for f in findings if f.severity == "FAIL")
    return fail_count == 0, findings
