"""
ECSS-E-ST-10-12C §5.6 — Phase-margin logic.
Radiation design margin (RDM) computation, phase-gate checks, and
hardness-assurance test-method validation. Stdlib only, offline.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ProjectPhase(str, Enum):
    PRE_PDR = "pre_pdr"
    PDR_CDR = "pdr_cdr"
    POST_CDR = "post_cdr"


class RadiationType(str, Enum):
    TID = "tid"
    DD = "dd"
    SEE_HEAVY_ION = "see_heavy_ion"
    SEE_PROTON = "see_proton"


class TestMethod(str, Enum):
    COBALT_60 = "cobalt_60"
    XRAY = "xray"
    ELDRS = "eldrs"
    PROTON = "proton"
    NEUTRON = "neutron"
    HEAVY_ION = "heavy_ion"
    SIMILARITY = "similarity"
    ANALYSIS_ONLY = "analysis_only"


# Minimum RDM required per radiation type and phase (§5.6.1–5.6.4).
# SEE types are not listed here — they use a qualification approach, not a
# numeric RDM gate.
MINIMUM_RDM: dict = {
    RadiationType.TID: {
        ProjectPhase.PRE_PDR: 2.0,
        ProjectPhase.PDR_CDR: 2.0,
        ProjectPhase.POST_CDR: 2.0,
    },
    RadiationType.DD: {
        ProjectPhase.PRE_PDR: 2.0,
        ProjectPhase.PDR_CDR: 2.0,
        ProjectPhase.POST_CDR: 2.0,
    },
}

# Accepted hardware test methods per radiation type (§5.6.5).
VALID_TEST_METHODS: dict = {
    RadiationType.TID: {TestMethod.COBALT_60, TestMethod.XRAY, TestMethod.ELDRS},
    RadiationType.DD: {TestMethod.PROTON, TestMethod.NEUTRON},
    RadiationType.SEE_HEAVY_ION: {TestMethod.HEAVY_ION},
    RadiationType.SEE_PROTON: {TestMethod.PROTON},
}

# Phases where analysis-only evidence is sufficient (no hardware test required).
_ANALYSIS_ACCEPTABLE = {ProjectPhase.PRE_PDR, ProjectPhase.PDR_CDR}


@dataclass
class RdmResult:
    rdm: float
    threshold: float
    compliant: bool
    radiation_type: str
    phase: str

    def status_label(self) -> str:
        """Categorize the margin as adequate, marginal, or inadequate."""
        if self.threshold == 0.0:
            return "adequate"
        if self.rdm >= self.threshold * 1.5:
            return "adequate"
        if self.rdm >= self.threshold:
            return "marginal"
        return "inadequate"


@dataclass
class TestMethodResult:
    radiation_type: str
    test_method: str
    phase: str
    valid: bool
    reason: str


@dataclass
class PhaseGateResult:
    phase: str
    findings: List[str] = field(default_factory=list)
    compliant: bool = True


def compute_rdm(device_tolerance: float, predicted_environment: float) -> float:
    """
    Compute radiation design margin: device tolerance divided by predicted
    mission environment value.

    Both arguments must be strictly positive (krad(Si) for TID, normalised
    fluence for DD, or any consistent unit pair). Raises ValueError otherwise.
    """
    if device_tolerance <= 0:
        raise ValueError(
            f"device_tolerance must be positive, got {device_tolerance}"
        )
    if predicted_environment <= 0:
        raise ValueError(
            f"predicted_environment must be positive, got {predicted_environment}"
        )
    return device_tolerance / predicted_environment


def check_rdm_compliance(
    rdm: float,
    radiation_type: RadiationType,
    phase: ProjectPhase,
) -> RdmResult:
    """
    Check whether an RDM value meets the minimum requirement for the given
    radiation type and project phase.

    SEE types (see_heavy_ion, see_proton) are not subject to a numeric RDM
    gate; this function returns compliant=True with threshold=0.0 for those
    types, signalling that a qualification approach must be checked separately.
    """
    if radiation_type not in MINIMUM_RDM:
        return RdmResult(
            rdm=rdm,
            threshold=0.0,
            compliant=True,
            radiation_type=radiation_type.value,
            phase=phase.value,
        )
    threshold = MINIMUM_RDM[radiation_type][phase]
    return RdmResult(
        rdm=rdm,
        threshold=threshold,
        compliant=rdm >= threshold,
        radiation_type=radiation_type.value,
        phase=phase.value,
    )


def validate_test_method(
    radiation_type: RadiationType,
    test_method: TestMethod,
    phase: ProjectPhase,
) -> TestMethodResult:
    """
    Validate that the chosen test method is appropriate for the radiation type
    and project phase.

    - ANALYSIS_ONLY is acceptable at pre-PDR and PDR-CDR; it is a compliance
      gap at post-CDR (§5.6.4 requires hardware test or verified similarity).
    - SIMILARITY is accepted at all phases when heritage evidence fully bounds
      the mission environment.
    - Hardware test methods are matched to radiation type via VALID_TEST_METHODS.
    """
    if test_method == TestMethod.ANALYSIS_ONLY:
        if phase in _ANALYSIS_ACCEPTABLE:
            return TestMethodResult(
                radiation_type=radiation_type.value,
                test_method=test_method.value,
                phase=phase.value,
                valid=True,
                reason="Analysis-only evidence is acceptable before CDR",
            )
        return TestMethodResult(
            radiation_type=radiation_type.value,
            test_method=test_method.value,
            phase=phase.value,
            valid=False,
            reason=(
                "Post-CDR hardness assurance requires hardware test data or "
                "verified heritage similarity — analysis alone is not sufficient"
            ),
        )

    if test_method == TestMethod.SIMILARITY:
        return TestMethodResult(
            radiation_type=radiation_type.value,
            test_method=test_method.value,
            phase=phase.value,
            valid=True,
            reason=(
                "Heritage similarity is accepted when prior test conditions "
                "fully bound the mission environment"
            ),
        )

    valid_methods = VALID_TEST_METHODS.get(radiation_type, set())
    if test_method in valid_methods:
        return TestMethodResult(
            radiation_type=radiation_type.value,
            test_method=test_method.value,
            phase=phase.value,
            valid=True,
            reason=f"Test method is applicable for {radiation_type.value}",
        )
    return TestMethodResult(
        radiation_type=radiation_type.value,
        test_method=test_method.value,
        phase=phase.value,
        valid=False,
        reason=(
            f"Test method '{test_method.value}' is not applicable for "
            f"'{radiation_type.value}'"
        ),
    )


def run_phase_gate(
    phase: ProjectPhase,
    rdm_results: List[RdmResult],
    test_method_results: List[TestMethodResult],
) -> PhaseGateResult:
    """
    Aggregate RDM compliance findings and test-method findings into a single
    phase-gate verdict. The gate passes only when every input result is
    compliant or valid.
    """
    findings: List[str] = []
    for r in rdm_results:
        if not r.compliant:
            findings.append(
                f"RDM {r.rdm:.2f} < required {r.threshold:.1f} "
                f"for {r.radiation_type} at {r.phase}"
            )
    for t in test_method_results:
        if not t.valid:
            findings.append(
                f"Invalid test method '{t.test_method}' for "
                f"{t.radiation_type} at {t.phase}: {t.reason}"
            )
    return PhaseGateResult(
        phase=phase.value,
        findings=findings,
        compliant=len(findings) == 0,
    )


def categorize_component_margin(rdm: float, threshold: float = 2.0) -> str:
    """
    Categorize a component's margin standing relative to the threshold.

    Returns one of three labels:
    - 'adequate'   : RDM >= 1.5 × threshold (comfortable margin)
    - 'marginal'   : threshold <= RDM < 1.5 × threshold (meets requirement, limited margin)
    - 'inadequate' : RDM < threshold (does not meet minimum requirement)
    """
    if threshold <= 0:
        raise ValueError(f"threshold must be positive, got {threshold}")
    if rdm < threshold:
        return "inadequate"
    if rdm < threshold * 1.5:
        return "marginal"
    return "adequate"
