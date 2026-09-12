"""
Strength functionality logic — ECSS-E-ST-32C clause 4.3.2.

Checks: no yielding at Design Yield Load (DYL), no failure at
Design Ultimate Load (DUL), applied at all levels of assembly.
Uses the von Mises criterion for multiaxial stress states.
stdlib only; deterministic; offline.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple

# Default factors of safety (representative; program document takes precedence)
DEFAULT_FOS_YIELD = 1.1
DEFAULT_FOS_ULTIMATE = 1.5

VALID_ASSEMBLY_LEVELS = {"component", "subsystem", "system"}


@dataclass
class StressState:
    """Six-component Cauchy stress tensor (MPa)."""
    sigma_x: float = 0.0
    sigma_y: float = 0.0
    sigma_z: float = 0.0
    tau_xy: float = 0.0
    tau_yz: float = 0.0
    tau_xz: float = 0.0


def von_mises_stress(s: StressState) -> float:
    """
    Von Mises equivalent stress from a full 3-D stress tensor.

    σ_vm = sqrt(0.5 * ((σx-σy)² + (σy-σz)² + (σz-σx)² + 6(τxy²+τyz²+τxz²)))
    """
    sx, sy, sz = s.sigma_x, s.sigma_y, s.sigma_z
    txy, tyz, txz = s.tau_xy, s.tau_yz, s.tau_xz
    radicand = 0.5 * (
        (sx - sy) ** 2
        + (sy - sz) ** 2
        + (sz - sx) ** 2
        + 6.0 * (txy ** 2 + tyz ** 2 + txz ** 2)
    )
    return math.sqrt(radicand)


def compute_dyl(limit_load: float, fos_yield: float = DEFAULT_FOS_YIELD) -> float:
    """Design Yield Load = limit load × yield factor of safety."""
    if fos_yield <= 0.0:
        raise ValueError(f"fos_yield must be positive, got {fos_yield}")
    if limit_load < 0.0:
        raise ValueError(f"limit_load must be non-negative, got {limit_load}")
    return limit_load * fos_yield


def compute_dul(limit_load: float, fos_ultimate: float = DEFAULT_FOS_ULTIMATE) -> float:
    """Design Ultimate Load = limit load × ultimate factor of safety."""
    if fos_ultimate <= 0.0:
        raise ValueError(f"fos_ultimate must be positive, got {fos_ultimate}")
    if limit_load < 0.0:
        raise ValueError(f"limit_load must be non-negative, got {limit_load}")
    return limit_load * fos_ultimate


def margin_of_safety(allowable: float, applied: float) -> float:
    """
    Margin of safety = allowable / applied − 1.

    Non-negative → pass.  Negative → non-compliance finding.
    """
    if applied <= 0.0:
        raise ValueError(f"applied stress must be positive, got {applied}")
    if allowable <= 0.0:
        raise ValueError(f"allowable must be positive, got {allowable}")
    return allowable / applied - 1.0


@dataclass
class StrengthCheck:
    """Inputs for a single assembly-level strength assessment."""
    assembly_level: str          # "component" | "subsystem" | "system"
    limit_load: float            # characteristic limit load (N, Nm, or equivalent scalar)
    stress_at_dyl: StressState   # stress tensor at DYL (MPa)
    stress_at_dul: StressState   # stress tensor at DUL (MPa)
    yield_strength: float        # material yield strength (MPa)
    ultimate_strength: float     # material ultimate strength (MPa)
    fos_yield: float = DEFAULT_FOS_YIELD
    fos_ultimate: float = DEFAULT_FOS_ULTIMATE


@dataclass
class StrengthResult:
    """Output of a single assembly-level strength assessment."""
    assembly_level: str
    dyl: float
    dul: float
    vm_stress_dyl: float
    vm_stress_dul: float
    mos_yield: float
    mos_ultimate: float
    yield_pass: bool    # True → no yielding at DYL
    ultimate_pass: bool  # True → no failure at DUL
    compliant: bool     # True → both gates pass


def assess_strength(check: StrengthCheck) -> StrengthResult:
    """
    Evaluate strength functionality for one assembly level.

    Raises ValueError for invalid inputs so callers receive an explicit
    error path rather than a silent bad result.
    """
    if check.assembly_level not in VALID_ASSEMBLY_LEVELS:
        raise ValueError(
            f"Unknown assembly level '{check.assembly_level}'. "
            f"Must be one of {sorted(VALID_ASSEMBLY_LEVELS)}."
        )
    if check.yield_strength <= 0.0:
        raise ValueError(f"yield_strength must be positive, got {check.yield_strength}")
    if check.ultimate_strength <= 0.0:
        raise ValueError(f"ultimate_strength must be positive, got {check.ultimate_strength}")
    if check.ultimate_strength < check.yield_strength:
        raise ValueError(
            f"ultimate_strength ({check.ultimate_strength}) must be >= "
            f"yield_strength ({check.yield_strength})"
        )
    if check.limit_load <= 0.0:
        raise ValueError(f"limit_load must be positive, got {check.limit_load}")
    if check.fos_ultimate < check.fos_yield:
        raise ValueError(
            f"fos_ultimate ({check.fos_ultimate}) must be >= fos_yield ({check.fos_yield})"
        )

    dyl = compute_dyl(check.limit_load, check.fos_yield)
    dul = compute_dul(check.limit_load, check.fos_ultimate)

    vm_dyl = von_mises_stress(check.stress_at_dyl)
    vm_dul = von_mises_stress(check.stress_at_dul)

    if vm_dyl <= 0.0:
        raise ValueError(
            "von Mises stress at DYL must be positive for a meaningful MoS check."
        )
    if vm_dul <= 0.0:
        raise ValueError(
            "von Mises stress at DUL must be positive for a meaningful MoS check."
        )

    mos_y = margin_of_safety(check.yield_strength, vm_dyl)
    mos_u = margin_of_safety(check.ultimate_strength, vm_dul)

    yield_pass = mos_y >= 0.0
    ultimate_pass = mos_u >= 0.0

    return StrengthResult(
        assembly_level=check.assembly_level,
        dyl=dyl,
        dul=dul,
        vm_stress_dyl=vm_dyl,
        vm_stress_dul=vm_dul,
        mos_yield=mos_y,
        mos_ultimate=mos_u,
        yield_pass=yield_pass,
        ultimate_pass=ultimate_pass,
        compliant=yield_pass and ultimate_pass,
    )


def assess_all_levels(
    checks: List[StrengthCheck],
) -> Tuple[List[StrengthResult], bool]:
    """
    Assess strength across multiple assembly levels.

    Returns (results, overall_compliant).  overall_compliant is True only
    when every level passes both yield and ultimate gates.
    """
    if not checks:
        raise ValueError("At least one StrengthCheck must be provided.")
    results = [assess_strength(c) for c in checks]
    overall = all(r.compliant for r in results)
    return results, overall
