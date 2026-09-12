"""
Static analysis verification logic — ECSS-E-ST-32C §4.6.2.3.

Verifies stress, strain, and stability margins against Design Yield Load (DYL)
and Design Ultimate Load (DUL) for calculix-linear, calculix-nonlinear, and
truss/beam hand-method analyses. stdlib only — no third-party dependencies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class LoadType(Enum):
    DYL = "DYL"
    DUL = "DUL"


class AnalysisMethod(Enum):
    CALCULIX_LINEAR = "calculix-linear"
    CALCULIX_NONLINEAR = "calculix-nonlinear"
    HAND_TRUSS = "hand-truss"
    HAND_BEAM = "hand-beam"


class VerificationStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


@dataclass
class StressResult:
    element_id: str
    applied_stress: float       # MPa; negative = compression
    allowable_stress: float     # MPa; must be positive
    load_type: LoadType
    analysis_method: AnalysisMethod


@dataclass
class StabilityResult:
    element_id: str
    critical_load: float        # N (after knock-down); must be positive
    applied_load: float         # N; must be positive
    load_type: LoadType
    analysis_method: AnalysisMethod


@dataclass
class MarginResult:
    element_id: str
    margin_of_safety: float
    status: VerificationStatus
    load_type: LoadType
    finding: str


def compute_margin_of_safety(allowable: float, applied: float) -> float:
    """
    MOS = (allowable / |applied|) - 1.

    Raises ValueError for non-positive allowable or zero applied.
    """
    if allowable <= 0.0:
        raise ValueError(f"Allowable must be positive, got {allowable}")
    if applied == 0.0:
        raise ValueError("Applied load/stress cannot be zero for MOS calculation")
    return (allowable / abs(applied)) - 1.0


def categorize_load(load_type: LoadType, yield_factor: float, ultimate_factor: float) -> dict:
    """
    Return design factor and acceptance threshold for a given load type.

    Both load types accept MOS >= 0.0.
    Raises ValueError for an unrecognised load type.
    """
    if load_type == LoadType.DYL:
        return {"factor": yield_factor, "min_mos": 0.0, "label": "DYL"}
    if load_type == LoadType.DUL:
        return {"factor": ultimate_factor, "min_mos": 0.0, "label": "DUL"}
    raise ValueError(f"Unknown load type: {load_type!r}")


def verify_stress(result: StressResult) -> MarginResult:
    """
    Verify one stress result against its allowable.

    Returns a MarginResult with PASS, FAIL, or ERROR status.
    """
    if result.allowable_stress <= 0.0:
        return MarginResult(
            element_id=result.element_id,
            margin_of_safety=float("-inf"),
            status=VerificationStatus.ERROR,
            load_type=result.load_type,
            finding=(
                f"Invalid allowable stress {result.allowable_stress} "
                f"for element {result.element_id}"
            ),
        )

    try:
        mos = compute_margin_of_safety(result.allowable_stress, result.applied_stress)
    except ValueError as exc:
        return MarginResult(
            element_id=result.element_id,
            margin_of_safety=float("-inf"),
            status=VerificationStatus.ERROR,
            load_type=result.load_type,
            finding=str(exc),
        )

    status = VerificationStatus.PASS if mos >= 0.0 else VerificationStatus.FAIL
    if status == VerificationStatus.PASS:
        finding = (
            f"Stress MOS = {mos:.4f} ({result.load_type.value}) "
            f"[{result.analysis_method.value}]"
        )
    else:
        finding = (
            f"Stress MOS = {mos:.4f} NEGATIVE ({result.load_type.value}) "
            f"— element {result.element_id} fails [{result.analysis_method.value}]"
        )

    return MarginResult(
        element_id=result.element_id,
        margin_of_safety=mos,
        status=status,
        load_type=result.load_type,
        finding=finding,
    )


def verify_stability(result: StabilityResult) -> MarginResult:
    """
    Verify a stability (buckling) result.

    RF = critical_load / applied_load; MOS = RF - 1.
    The critical_load must already include any knock-down factor.
    Returns a MarginResult with PASS, FAIL, or ERROR status.
    """
    if result.critical_load <= 0.0:
        return MarginResult(
            element_id=result.element_id,
            margin_of_safety=float("-inf"),
            status=VerificationStatus.ERROR,
            load_type=result.load_type,
            finding=(
                f"Critical load must be positive, got {result.critical_load} "
                f"for element {result.element_id}"
            ),
        )
    if result.applied_load <= 0.0:
        return MarginResult(
            element_id=result.element_id,
            margin_of_safety=float("-inf"),
            status=VerificationStatus.ERROR,
            load_type=result.load_type,
            finding=(
                f"Applied load must be positive for stability check, "
                f"got {result.applied_load} for element {result.element_id}"
            ),
        )

    rf = result.critical_load / result.applied_load
    mos = rf - 1.0

    status = VerificationStatus.PASS if mos >= 0.0 else VerificationStatus.FAIL
    if status == VerificationStatus.PASS:
        finding = (
            f"Stability RF = {rf:.4f}, MOS = {mos:.4f} ({result.load_type.value}) "
            f"[{result.analysis_method.value}]"
        )
    else:
        finding = (
            f"Stability RF = {rf:.4f}, MOS = {mos:.4f} NEGATIVE "
            f"({result.load_type.value}) — element {result.element_id} buckles "
            f"[{result.analysis_method.value}]"
        )

    return MarginResult(
        element_id=result.element_id,
        margin_of_safety=mos,
        status=status,
        load_type=result.load_type,
        finding=finding,
    )


def run_analysis_verification(
    stress_results: List[StressResult],
    stability_results: List[StabilityResult],
) -> dict:
    """
    Run the full static-analysis verification across all supplied results.

    Returns a summary dict with:
      overall_status   — PASS / FAIL / ERROR
      margins          — list of MarginResult
      failure_count    — number of FAIL records
      error_count      — number of ERROR records
      total_checks     — total number of checks performed
    """
    margins: List[MarginResult] = []

    for sr in stress_results:
        margins.append(verify_stress(sr))

    for stab in stability_results:
        margins.append(verify_stability(stab))

    failures = [r for r in margins if r.status == VerificationStatus.FAIL]
    errors = [r for r in margins if r.status == VerificationStatus.ERROR]

    if errors:
        overall = VerificationStatus.ERROR
    elif failures:
        overall = VerificationStatus.FAIL
    else:
        overall = VerificationStatus.PASS

    return {
        "overall_status": overall,
        "margins": margins,
        "failure_count": len(failures),
        "error_count": len(errors),
        "total_checks": len(margins),
    }
