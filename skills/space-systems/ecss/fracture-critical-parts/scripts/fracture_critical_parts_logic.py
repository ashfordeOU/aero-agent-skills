"""
Fracture-critical-part screening and fracture control verification.
Reference: ECSS-E-ST-32C clause 4.2.2 (paraphrased; no verbatim standard text).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class FailureConsequence(Enum):
    CATASTROPHIC = 4
    CRITICAL = 3
    MAJOR = 2
    MINOR = 1


class StructuralRole(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    NON_STRUCTURAL = "non_structural"


class FractureControlMethod(Enum):
    PROOF_TEST = "proof_test"
    NDE = "nde"
    BOTH = "both"
    NONE = "none"


# Minimum proof factor for primary metallic structure.
# Reference: ECSS-E-ST-32C §4.2.2 (paraphrased); check programme FCP for actual limit.
MIN_PROOF_FACTOR = 1.25

# NDE must detect cracks at most (critical_crack_size / NDE_MARGIN) mm.
# Ensures a factor-of-two margin between detectability and criticality.
NDE_MARGIN = 2.0


@dataclass
class PartRecord:
    part_id: str
    material: str
    consequence: FailureConsequence
    structural_role: StructuralRole
    applied_stress_mpa: float
    yield_strength_mpa: float
    fracture_toughness_mpa_sqrtm: float
    is_pressurized: bool
    proof_factor: Optional[float] = None
    nde_detectable_crack_mm: Optional[float] = None
    critical_crack_size_mm: Optional[float] = None
    fracture_control_method: FractureControlMethod = FractureControlMethod.NONE

    def stress_ratio(self) -> float:
        if self.yield_strength_mpa <= 0:
            raise ValueError(
                f"Part {self.part_id}: yield_strength_mpa must be > 0, got {self.yield_strength_mpa}"
            )
        return self.applied_stress_mpa / self.yield_strength_mpa


@dataclass
class ScreeningResult:
    part_id: str
    is_fracture_critical: bool
    reasons: List[str]


@dataclass
class ControlComplianceResult:
    part_id: str
    method: FractureControlMethod
    compliant: bool
    findings: List[str]


def _validate_part(part: PartRecord) -> None:
    if part.yield_strength_mpa <= 0:
        raise ValueError(
            f"Part {part.part_id}: yield_strength_mpa must be > 0, got {part.yield_strength_mpa}"
        )
    if part.applied_stress_mpa < 0:
        raise ValueError(
            f"Part {part.part_id}: applied_stress_mpa must be >= 0, got {part.applied_stress_mpa}"
        )
    if part.fracture_toughness_mpa_sqrtm <= 0:
        raise ValueError(
            f"Part {part.part_id}: fracture_toughness_mpa_sqrtm must be > 0, "
            f"got {part.fracture_toughness_mpa_sqrtm}"
        )


def screen_fracture_critical(part: PartRecord) -> ScreeningResult:
    """
    Screen a part for fracture criticality.

    A part is fracture critical when consequence is CATASTROPHIC or CRITICAL
    AND at least one structural trigger applies:
      - part is pressurized
      - structural role is PRIMARY
      - stress ratio (applied / yield) >= 0.50
    """
    _validate_part(part)

    reasons: List[str] = []
    is_fracture_critical = False

    consequence_qualifies = part.consequence in (
        FailureConsequence.CATASTROPHIC,
        FailureConsequence.CRITICAL,
    )

    if not consequence_qualifies:
        reasons.append(
            f"consequence {part.consequence.name} is below the catastrophic/critical threshold"
        )
        return ScreeningResult(
            part_id=part.part_id,
            is_fracture_critical=False,
            reasons=reasons,
        )

    if part.is_pressurized:
        reasons.append(
            f"pressurized part with {part.consequence.name} consequence"
        )
        is_fracture_critical = True

    if part.structural_role == StructuralRole.PRIMARY:
        reasons.append(
            f"primary structure with {part.consequence.name} consequence"
        )
        is_fracture_critical = True

    ratio = part.stress_ratio()
    if ratio >= 0.50:
        reasons.append(
            f"stress ratio {ratio:.3f} >= 0.50 with {part.consequence.name} consequence"
        )
        is_fracture_critical = True

    if not is_fracture_critical:
        reasons.append(
            f"{part.consequence.name} consequence but no structural trigger met "
            f"(not pressurized, not primary, stress ratio {ratio:.3f} < 0.50)"
        )

    return ScreeningResult(
        part_id=part.part_id,
        is_fracture_critical=is_fracture_critical,
        reasons=reasons,
    )


def compute_proof_detectable_crack_mm(
    critical_crack_size_mm: float,
    proof_factor: float,
) -> float:
    """
    Return the largest crack that can survive a proof test.

    Stress intensity K ~ stress * sqrt(crack_size).  At proof load the stress
    is (proof_factor * limit_stress).  A crack at critical_crack_size_mm is
    exactly critical at limit load; after the proof the maximum surviving crack
    scales as critical / proof_factor^2.
    """
    if proof_factor <= 1.0:
        raise ValueError(f"proof_factor must be > 1.0, got {proof_factor}")
    if critical_crack_size_mm <= 0:
        raise ValueError(
            f"critical_crack_size_mm must be > 0, got {critical_crack_size_mm}"
        )
    return critical_crack_size_mm / (proof_factor ** 2)


def check_proof_test_compliance(part: PartRecord) -> Tuple[bool, List[str]]:
    """Verify proof test inputs meet fracture control requirements."""
    findings: List[str] = []

    if part.proof_factor is None:
        findings.append(f"{part.part_id}: proof_factor not specified")
        return False, findings

    if part.proof_factor <= 1.0:
        findings.append(
            f"{part.part_id}: proof_factor {part.proof_factor:.3f} must be > 1.0"
        )
        return False, findings

    if part.proof_factor < MIN_PROOF_FACTOR:
        findings.append(
            f"{part.part_id}: proof_factor {part.proof_factor:.3f} < minimum {MIN_PROOF_FACTOR}"
        )
        return False, findings

    if part.critical_crack_size_mm is None:
        findings.append(
            f"{part.part_id}: critical_crack_size_mm not specified; "
            "proof test margin cannot be verified"
        )
        return False, findings

    if part.critical_crack_size_mm <= 0:
        findings.append(
            f"{part.part_id}: critical_crack_size_mm must be > 0, "
            f"got {part.critical_crack_size_mm}"
        )
        return False, findings

    return True, []


def check_nde_compliance(part: PartRecord) -> Tuple[bool, List[str]]:
    """Verify that NDE inspection sensitivity meets the required margin."""
    findings: List[str] = []

    if part.nde_detectable_crack_mm is None:
        findings.append(f"{part.part_id}: nde_detectable_crack_mm not specified")
        return False, findings

    if part.nde_detectable_crack_mm <= 0:
        findings.append(
            f"{part.part_id}: nde_detectable_crack_mm must be > 0, "
            f"got {part.nde_detectable_crack_mm}"
        )
        return False, findings

    if part.critical_crack_size_mm is None:
        findings.append(
            f"{part.part_id}: critical_crack_size_mm not specified; "
            "NDE margin cannot be verified"
        )
        return False, findings

    if part.critical_crack_size_mm <= 0:
        findings.append(
            f"{part.part_id}: critical_crack_size_mm must be > 0, "
            f"got {part.critical_crack_size_mm}"
        )
        return False, findings

    required_detectable = part.critical_crack_size_mm / NDE_MARGIN
    if part.nde_detectable_crack_mm > required_detectable:
        findings.append(
            f"{part.part_id}: NDE detectable crack {part.nde_detectable_crack_mm:.3f} mm "
            f"> required limit {required_detectable:.3f} mm "
            f"(critical {part.critical_crack_size_mm:.3f} mm / margin {NDE_MARGIN})"
        )
        return False, findings

    return True, []


def evaluate_fracture_control_compliance(part: PartRecord) -> ControlComplianceResult:
    """
    Evaluate full fracture control compliance for a part.

    Non-fracture-critical parts are returned as compliant with method NONE.
    Fracture-critical parts must have a method assigned and all
    method-specific checks must pass.
    """
    _validate_part(part)

    screening = screen_fracture_critical(part)
    if not screening.is_fracture_critical:
        return ControlComplianceResult(
            part_id=part.part_id,
            method=FractureControlMethod.NONE,
            compliant=True,
            findings=[],
        )

    method = part.fracture_control_method
    all_findings: List[str] = []

    if method == FractureControlMethod.NONE:
        all_findings.append(
            f"{part.part_id}: fracture-critical part has no fracture control method assigned"
        )
        return ControlComplianceResult(
            part_id=part.part_id,
            method=method,
            compliant=False,
            findings=all_findings,
        )

    if method in (FractureControlMethod.PROOF_TEST, FractureControlMethod.BOTH):
        _, findings = check_proof_test_compliance(part)
        all_findings.extend(findings)

    if method in (FractureControlMethod.NDE, FractureControlMethod.BOTH):
        _, findings = check_nde_compliance(part)
        all_findings.extend(findings)

    return ControlComplianceResult(
        part_id=part.part_id,
        method=method,
        compliant=len(all_findings) == 0,
        findings=all_findings,
    )
