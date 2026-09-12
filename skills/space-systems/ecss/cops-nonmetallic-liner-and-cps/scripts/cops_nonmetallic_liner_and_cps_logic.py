"""
COPS non-metallic liner and all-composite CPS assessment logic.
Implements checks per ECSS-E-ST-32 clause 4.4.4 (paraphrased).
stdlib only — no external dependencies.
"""

from enum import Enum
from typing import List, Optional

# ---------------------------------------------------------------------------
# System variant
# ---------------------------------------------------------------------------

class SystemVariant(Enum):
    COPS_NONMETALLIC_LINER = "cops_nonmetallic_liner"
    ALL_COMPOSITE_CPS = "all_composite_cps"


# ---------------------------------------------------------------------------
# ECSS-E-ST-32 clause 4.4.4 representative safety factors (paraphrased)
# ---------------------------------------------------------------------------

PROOF_FACTOR: float = 1.1   # proof pressure >= MEOP × 1.1
BURST_FACTOR: float = 2.0   # predicted burst >= MEOP × 2.0
CYCLE_LIFE_FACTOR: int = 4  # qualified cycles >= design_cycles × 4
MIN_BUCKLING_RATIO: float = 1.0  # critical_ext_p / applied_ext_p >= 1.0


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class PressureSystemInput:
    """All inputs required to assess one COPS/CPS item."""

    def __init__(
        self,
        variant: SystemVariant,
        meop_mpa: float,
        proof_pressure_mpa: float,
        burst_pressure_predicted_mpa: float,
        design_cycles: int,
        qualified_cycles: int,
        lbb_demonstrated: bool,
        safe_life_approach: bool,
        permeation_rate_cc_per_s: Optional[float] = None,
        allowable_permeation_cc_per_s: Optional[float] = None,
        liner_buckling_ratio: Optional[float] = None,
    ) -> None:
        self.variant = variant
        self.meop_mpa = meop_mpa
        self.proof_pressure_mpa = proof_pressure_mpa
        self.burst_pressure_predicted_mpa = burst_pressure_predicted_mpa
        self.design_cycles = design_cycles
        self.qualified_cycles = qualified_cycles
        self.lbb_demonstrated = lbb_demonstrated
        self.safe_life_approach = safe_life_approach
        self.permeation_rate_cc_per_s = permeation_rate_cc_per_s
        self.allowable_permeation_cc_per_s = allowable_permeation_cc_per_s
        self.liner_buckling_ratio = liner_buckling_ratio


class FindingItem:
    """One check result."""

    def __init__(self, check: str, status: str, detail: str) -> None:
        if status not in ("PASS", "FAIL"):
            raise ValueError(f"status must be PASS or FAIL, got {status!r}")
        self.check = check
        self.status = status
        self.detail = detail

    def __repr__(self) -> str:
        return f"FindingItem({self.check!r}, {self.status!r}, {self.detail!r})"


class AssessmentResult:
    """Aggregate result for one pressure system item."""

    def __init__(self, variant: str, findings: List[FindingItem]) -> None:
        self.variant = variant
        self.findings = findings

    @property
    def compliant(self) -> bool:
        return all(f.status == "PASS" for f in self.findings)

    def fails(self) -> List[FindingItem]:
        return [f for f in self.findings if f.status == "FAIL"]


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_proof_margin(meop: float, proof: float) -> FindingItem:
    required = meop * PROOF_FACTOR
    if proof >= required:
        return FindingItem(
            "proof_pressure",
            "PASS",
            f"{proof:.3f} MPa >= {required:.3f} MPa (MEOP × {PROOF_FACTOR})",
        )
    return FindingItem(
        "proof_pressure",
        "FAIL",
        f"{proof:.3f} MPa < {required:.3f} MPa required (MEOP × {PROOF_FACTOR})",
    )


def check_burst_margin(meop: float, burst: float) -> FindingItem:
    required = meop * BURST_FACTOR
    if burst >= required:
        return FindingItem(
            "burst_pressure",
            "PASS",
            f"{burst:.3f} MPa >= {required:.3f} MPa (MEOP × {BURST_FACTOR})",
        )
    return FindingItem(
        "burst_pressure",
        "FAIL",
        f"{burst:.3f} MPa < {required:.3f} MPa required (MEOP × {BURST_FACTOR})",
    )


def check_cycle_life(design_cycles: int, qualified_cycles: int) -> FindingItem:
    required = design_cycles * CYCLE_LIFE_FACTOR
    if qualified_cycles >= required:
        return FindingItem(
            "cycle_life",
            "PASS",
            f"{qualified_cycles} cycles qualified >= {required} required (design × {CYCLE_LIFE_FACTOR})",
        )
    return FindingItem(
        "cycle_life",
        "FAIL",
        f"{qualified_cycles} cycles qualified < {required} required (design × {CYCLE_LIFE_FACTOR})",
    )


def check_fracture_control(lbb_demonstrated: bool, safe_life_approach: bool) -> FindingItem:
    if lbb_demonstrated:
        return FindingItem(
            "fracture_control",
            "PASS",
            "Leak-before-burst capability demonstrated",
        )
    if safe_life_approach:
        return FindingItem(
            "fracture_control",
            "PASS",
            "safe-life fracture control approach documented",
        )
    return FindingItem(
        "fracture_control",
        "FAIL",
        "Neither LBB capability nor safe-life approach is on record",
    )


def check_liner_permeation(
    rate: Optional[float], allowable: Optional[float]
) -> FindingItem:
    if rate is None:
        return FindingItem(
            "liner_permeation",
            "FAIL",
            "Permeation rate not provided for non-metallic liner variant",
        )
    if allowable is None:
        return FindingItem(
            "liner_permeation",
            "FAIL",
            "Allowable permeation not provided for non-metallic liner variant",
        )
    if rate <= allowable:
        return FindingItem(
            "liner_permeation",
            "PASS",
            f"{rate:.3e} cc/s <= {allowable:.3e} cc/s allowable",
        )
    return FindingItem(
        "liner_permeation",
        "FAIL",
        f"{rate:.3e} cc/s > {allowable:.3e} cc/s allowable (permeation budget exceeded)",
    )


def check_liner_buckling(ratio: Optional[float]) -> FindingItem:
    if ratio is None:
        return FindingItem(
            "liner_buckling",
            "FAIL",
            "Liner buckling ratio (critical/applied external pressure) not provided",
        )
    if ratio >= MIN_BUCKLING_RATIO:
        return FindingItem(
            "liner_buckling",
            "PASS",
            f"Buckling ratio {ratio:.3f} >= {MIN_BUCKLING_RATIO:.1f} (no buckling risk)",
        )
    return FindingItem(
        "liner_buckling",
        "FAIL",
        f"Buckling ratio {ratio:.3f} < {MIN_BUCKLING_RATIO:.1f} (liner buckling risk)",
    )


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validate_inputs(inp: PressureSystemInput) -> None:
    if inp.meop_mpa <= 0.0:
        raise ValueError(f"MEOP must be positive, got {inp.meop_mpa}")
    if inp.proof_pressure_mpa <= 0.0:
        raise ValueError(f"Proof pressure must be positive, got {inp.proof_pressure_mpa}")
    if inp.burst_pressure_predicted_mpa <= 0.0:
        raise ValueError(f"Burst pressure must be positive, got {inp.burst_pressure_predicted_mpa}")
    if inp.design_cycles < 0:
        raise ValueError(f"Design cycles must be non-negative, got {inp.design_cycles}")
    if inp.qualified_cycles < 0:
        raise ValueError(f"Qualified cycles must be non-negative, got {inp.qualified_cycles}")
    if inp.permeation_rate_cc_per_s is not None and inp.permeation_rate_cc_per_s < 0.0:
        raise ValueError("Permeation rate must be non-negative")
    if inp.allowable_permeation_cc_per_s is not None and inp.allowable_permeation_cc_per_s < 0.0:
        raise ValueError("Allowable permeation must be non-negative")


# ---------------------------------------------------------------------------
# Top-level assessment
# ---------------------------------------------------------------------------

def assess_system(inp: PressureSystemInput) -> AssessmentResult:
    """
    Run all clause 4.4.4 checks for the given COPS/CPS input.
    Raises ValueError on invalid inputs.
    Returns AssessmentResult with per-check findings.
    """
    _validate_inputs(inp)

    findings: List[FindingItem] = [
        check_proof_margin(inp.meop_mpa, inp.proof_pressure_mpa),
        check_burst_margin(inp.meop_mpa, inp.burst_pressure_predicted_mpa),
        check_cycle_life(inp.design_cycles, inp.qualified_cycles),
        check_fracture_control(inp.lbb_demonstrated, inp.safe_life_approach),
    ]

    if inp.variant == SystemVariant.COPS_NONMETALLIC_LINER:
        findings.append(
            check_liner_permeation(
                inp.permeation_rate_cc_per_s,
                inp.allowable_permeation_cc_per_s,
            )
        )
        findings.append(check_liner_buckling(inp.liner_buckling_ratio))

    return AssessmentResult(variant=inp.variant.value, findings=findings)


# ---------------------------------------------------------------------------
# Convenience: margin summary
# ---------------------------------------------------------------------------

def burst_margin_ratio(meop_mpa: float, burst_mpa: float) -> float:
    """Return burst / (MEOP × burst_factor); > 1.0 means compliant."""
    if meop_mpa <= 0.0:
        raise ValueError("MEOP must be positive")
    return burst_mpa / (meop_mpa * BURST_FACTOR)


def proof_margin_ratio(meop_mpa: float, proof_mpa: float) -> float:
    """Return proof / (MEOP × proof_factor); > 1.0 means compliant."""
    if meop_mpa <= 0.0:
        raise ValueError("MEOP must be positive")
    return proof_mpa / (meop_mpa * PROOF_FACTOR)
