"""
Metallic pressurized structure (MPS) engineering logic.
ECSS-E-ST-32C clause 4.4.2 — paraphrased procedure.
Stdlib only. Deterministic, offline.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple


class StructureCategory(Enum):
    """Whether the structure is part of a manned or unmanned assembly."""
    UNMANNED = "unmanned"
    MANNED = "manned"


class BulkheadDesignation(Enum):
    """Safety designation for a pressure bulkhead."""
    SAFETY_CRITICAL = "safety_critical"
    NON_SAFETY_CRITICAL = "non_safety_critical"


@dataclass
class ThinWallGeometry:
    """Thin-wall cylinder geometry parameters."""
    radius: float    # Mean radius [m], must be > 0
    thickness: float # Wall thickness [m], must be > 0


@dataclass
class MPSResult:
    """Outcome of a full MPS compliance assessment."""
    mos_hoop: float
    mos_axial: float
    dup: float
    hoop_stress: float
    axial_stress: float
    proof_pressure: float
    burst_pressure: float
    bulkhead_compliant: bool
    compliant: bool
    findings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Stress primitives
# ---------------------------------------------------------------------------

def compute_hoop_stress(pressure: float, radius: float, thickness: float) -> float:
    """
    Thin-wall hoop (circumferential) stress: σ_h = p · r / t [Pa].

    Raises ValueError for non-physical geometry or negative pressure.
    """
    if pressure < 0:
        raise ValueError(f"Pressure must be ≥ 0, got {pressure}")
    if radius <= 0:
        raise ValueError(f"Radius must be > 0, got {radius}")
    if thickness <= 0:
        raise ValueError(f"Thickness must be > 0, got {thickness}")
    return pressure * radius / thickness


def compute_axial_stress(
    pressure: float,
    radius: float,
    thickness: float,
    axial_load: float,
) -> float:
    """
    Combined axial stress at a closed-end thin-wall cylinder cross-section.

    σ_a = p·r/(2t)  +  N / (2π·r·t)

    where N is the net axial force [N] (positive = tension).
    Raises ValueError for non-physical geometry or negative pressure.
    """
    if pressure < 0:
        raise ValueError(f"Pressure must be ≥ 0, got {pressure}")
    if radius <= 0:
        raise ValueError(f"Radius must be > 0, got {radius}")
    if thickness <= 0:
        raise ValueError(f"Thickness must be > 0, got {thickness}")
    wall_area = 2.0 * math.pi * radius * thickness
    pressure_component = pressure * radius / (2.0 * thickness)
    mechanical_component = axial_load / wall_area
    return pressure_component + mechanical_component


# ---------------------------------------------------------------------------
# Pressure design levels
# ---------------------------------------------------------------------------

def compute_design_ultimate_pressure(meop: float, pressure_sf: float) -> float:
    """
    Design Ultimate Pressure = MEOP × pressure safety factor.

    Raises ValueError if MEOP ≤ 0 or pressure_sf < 1.0.
    """
    if meop <= 0:
        raise ValueError(f"MEOP must be > 0, got {meop}")
    if pressure_sf < 1.0:
        raise ValueError(f"Pressure safety factor must be ≥ 1.0, got {pressure_sf}")
    return meop * pressure_sf


def compute_proof_pressure(meop: float) -> float:
    """
    Minimum proof test pressure for metallic pressurized hardware: 1.1 × MEOP.

    Raises ValueError if MEOP ≤ 0.
    """
    if meop <= 0:
        raise ValueError(f"MEOP must be > 0, got {meop}")
    return meop * 1.1


def compute_burst_pressure(meop: float) -> float:
    """
    Minimum burst pressure requirement for metallic pressurized hardware: 2.0 × MEOP.

    Raises ValueError if MEOP ≤ 0.
    """
    if meop <= 0:
        raise ValueError(f"MEOP must be > 0, got {meop}")
    return meop * 2.0


# ---------------------------------------------------------------------------
# Margin of safety
# ---------------------------------------------------------------------------

def compute_margin_of_safety(allowable: float, applied: float) -> float:
    """
    MoS = (allowable / applied) − 1.

    MoS ≥ 0 is required for structural compliance.
    Raises ValueError for non-positive inputs.
    """
    if allowable <= 0:
        raise ValueError(f"Allowable must be > 0, got {allowable}")
    if applied <= 0:
        raise ValueError(f"Applied load/stress must be > 0, got {applied}")
    return (allowable / applied) - 1.0


# ---------------------------------------------------------------------------
# Pressure bulkhead fail-safe check
# ---------------------------------------------------------------------------

def assess_pressure_bulkhead(
    designation: BulkheadDesignation,
    has_fail_safe_feature: bool,
    has_redundant_load_path: bool,
) -> Tuple[bool, List[str]]:
    """
    Check that a Safety-critical pressure bulkhead has at least one of:
    a fail-safe structural feature or a redundant load path.

    Non-Safety-critical bulkheads always pass this check.
    Returns (compliant: bool, findings: list[str]).
    """
    findings: List[str] = []
    if designation == BulkheadDesignation.SAFETY_CRITICAL:
        if not has_fail_safe_feature and not has_redundant_load_path:
            findings.append(
                "Safety-critical pressure bulkhead has neither a fail-safe "
                "structural feature nor a redundant load path — "
                "a single structural failure can result in loss of pressure "
                "containment; design must be resolved before compliance."
            )
            return False, findings
    return True, findings


# ---------------------------------------------------------------------------
# Full MPS compliance assessment
# ---------------------------------------------------------------------------

def assess_mps_compliance(
    geometry: ThinWallGeometry,
    meop: float,
    pressure_sf: float,
    allowable_hoop: float,
    allowable_axial: float,
    axial_load: float,
    bulkhead_designation: BulkheadDesignation,
    has_fail_safe_feature: bool,
    has_redundant_load_path: bool,
) -> MPSResult:
    """
    Full MPS structural compliance assessment per ECSS-E-ST-32C §4.4.2.

    Steps:
      1. Derive DUP, proof pressure, burst pressure.
      2. Compute thin-wall hoop and axial stresses at DUP + axial_load.
      3. Evaluate MoS for both stress components.
      4. Assess pressure bulkhead fail-safe provision.
      5. Aggregate findings; set compliant flag.

    Raises ValueError for invalid inputs (delegates to sub-functions).
    """
    findings: List[str] = []

    dup = compute_design_ultimate_pressure(meop, pressure_sf)
    proof_pressure = compute_proof_pressure(meop)
    burst_pressure = compute_burst_pressure(meop)

    hoop_stress = compute_hoop_stress(dup, geometry.radius, geometry.thickness)
    axial_stress = compute_axial_stress(
        dup, geometry.radius, geometry.thickness, axial_load
    )

    mos_hoop = compute_margin_of_safety(allowable_hoop, hoop_stress)
    mos_axial = compute_margin_of_safety(allowable_axial, axial_stress)

    if mos_hoop < 0.0:
        findings.append(
            f"Hoop stress MoS = {mos_hoop:.4f} (negative) — "
            "structure does not meet the hoop strength requirement at DUL."
        )
    if mos_axial < 0.0:
        findings.append(
            f"Axial stress MoS = {mos_axial:.4f} (negative) — "
            "structure does not meet the axial strength requirement at DUL."
        )

    bulkhead_ok, bulkhead_findings = assess_pressure_bulkhead(
        bulkhead_designation, has_fail_safe_feature, has_redundant_load_path
    )
    findings.extend(bulkhead_findings)

    compliant = (mos_hoop >= 0.0) and (mos_axial >= 0.0) and bulkhead_ok

    return MPSResult(
        mos_hoop=mos_hoop,
        mos_axial=mos_axial,
        dup=dup,
        hoop_stress=hoop_stress,
        axial_stress=axial_stress,
        proof_pressure=proof_pressure,
        burst_pressure=burst_pressure,
        bulkhead_compliant=bulkhead_ok,
        compliant=compliant,
        findings=findings,
    )
