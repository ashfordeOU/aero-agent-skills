"""
Weld fracture-control logic — ECSS-E-ST-32C clause 8.3.
Covers weld quality class assignment, ISO 6520-1 imperfection screening,
safe-life fatigue assessment, and NDT coverage verification.
Stdlib only. Offline, deterministic.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Weld quality classes
# ---------------------------------------------------------------------------

class WeldClass(Enum):
    A = "A"  # Fracture-critical — highest quality / inspection requirement
    B = "B"  # Primary load-carrying structure, not fracture-critical
    C = "C"  # Secondary or non-structural members


# Minimum safe-life factor (allowable cycles / applied cycles) by class.
# Paraphrased from ECSS-E-ST-32C clause 8.3 guidance — not verbatim.
REQUIRED_SAFE_LIFE_FACTOR: Dict[WeldClass, float] = {
    WeldClass.A: 4.0,
    WeldClass.B: 2.0,
    WeldClass.C: 1.5,
}

# Required NDT coverage fraction (0–1) by class.
REQUIRED_NDT_COVERAGE: Dict[WeldClass, float] = {
    WeldClass.A: 1.0,   # 100% — full volumetric inspection
    WeldClass.B: 0.5,   # 50% minimum
    WeldClass.C: 0.1,   # spot-check
}


# ---------------------------------------------------------------------------
# ISO 6520-1 imperfection groups
# ---------------------------------------------------------------------------

class ImperfectionGroup(Enum):
    CRACKS = 100
    CAVITIES = 200
    SOLID_INCLUSIONS = 300
    LACK_OF_FUSION = 400
    IMPERFECT_SHAPE = 500
    MISCELLANEOUS = 600


# Maximum acceptable imperfection size (mm) per group and class.
# Cracks and lack-of-fusion: zero tolerance for A and B.
# Paraphrased limits derived from ECSS-E-ST-32C clause 8.3 / ISO 5817 linkage.
IMPERFECTION_LIMIT_MM: Dict[ImperfectionGroup, Dict[WeldClass, float]] = {
    ImperfectionGroup.CRACKS: {
        WeldClass.A: 0.0,
        WeldClass.B: 0.0,
        WeldClass.C: 0.0,   # cracks not acceptable in any class
    },
    ImperfectionGroup.CAVITIES: {
        WeldClass.A: 0.5,
        WeldClass.B: 1.0,
        WeldClass.C: 2.0,
    },
    ImperfectionGroup.SOLID_INCLUSIONS: {
        WeldClass.A: 0.5,
        WeldClass.B: 1.5,
        WeldClass.C: 2.5,
    },
    ImperfectionGroup.LACK_OF_FUSION: {
        WeldClass.A: 0.0,
        WeldClass.B: 0.0,
        WeldClass.C: 0.5,
    },
    ImperfectionGroup.IMPERFECT_SHAPE: {
        WeldClass.A: 0.3,
        WeldClass.B: 0.6,
        WeldClass.C: 1.0,
    },
    ImperfectionGroup.MISCELLANEOUS: {
        WeldClass.A: 0.5,
        WeldClass.B: 1.0,
        WeldClass.C: 2.0,
    },
}


# ---------------------------------------------------------------------------
# NDT methods
# ---------------------------------------------------------------------------

class NdtMethod(Enum):
    UT = "UT"   # Ultrasonic Testing — volumetric
    RT = "RT"   # Radiographic Testing — volumetric
    PT = "PT"   # Penetrant Testing — surface only
    MT = "MT"   # Magnetic Particle Testing — surface only
    VT = "VT"   # Visual Testing — surface only


# Minimum detectable flaw size (mm) for each method under standard conditions.
# Paraphrased engineering guidance — not verbatim from any standard.
NDT_MIN_DETECTABLE_MM: Dict[NdtMethod, float] = {
    NdtMethod.UT: 1.0,
    NdtMethod.RT: 0.5,
    NdtMethod.PT: 0.1,
    NdtMethod.MT: 0.1,
    NdtMethod.VT: 2.0,
}

VOLUMETRIC_METHODS = frozenset({NdtMethod.UT, NdtMethod.RT})


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class WeldImperfection:
    group: ImperfectionGroup
    size_mm: float
    location: str = "unspecified"


@dataclass
class ImperfectionResult:
    imperfection: WeldImperfection
    limit_mm: float
    passed: bool
    note: str


@dataclass
class FatigueResult:
    usage_fraction: float       # applied_cycles / allowable_cycles
    safe_life_factor: float     # allowable_cycles / applied_cycles
    required_factor: float
    passed: bool
    note: str


@dataclass
class NdtResult:
    coverage_passed: bool
    flaw_detection_passed: bool
    has_volumetric: bool
    min_detectable_mm: float
    required_coverage: float
    note: str


@dataclass
class WeldAssessment:
    weld_id: str
    weld_class: WeldClass
    imperfections: List[WeldImperfection] = field(default_factory=list)
    applied_cycles: Optional[float] = None
    allowable_cycles: Optional[float] = None
    ndt_methods: List[NdtMethod] = field(default_factory=list)
    ndt_coverage_fraction: float = 0.0
    assumed_initial_flaw_mm: Optional[float] = None


@dataclass
class WeldAssessmentResult:
    weld_id: str
    weld_class: WeldClass
    imperfection_results: List[ImperfectionResult]
    fatigue_result: Optional[FatigueResult]
    ndt_result: Optional[NdtResult]
    compliant: bool
    findings: List[str]


# ---------------------------------------------------------------------------
# Core logic functions
# ---------------------------------------------------------------------------

def assign_weld_class(
    is_fracture_critical: bool,
    is_primary_structure: bool,
) -> WeldClass:
    """
    Assign a weld quality class based on structural role and criticality.
    Class A: fracture-critical welds.
    Class B: primary structure, not fracture-critical.
    Class C: secondary or non-structural.
    Mirrors ECSS-E-ST-32C clause 8.3 assignment logic (paraphrased).
    """
    if is_fracture_critical:
        return WeldClass.A
    if is_primary_structure:
        return WeldClass.B
    return WeldClass.C


def screen_imperfection(
    imperfection: WeldImperfection,
    weld_class: WeldClass,
) -> ImperfectionResult:
    """
    Compare a single ISO 6520-1 imperfection to the acceptance limit
    for the given weld class. Returns pass/fail with the applicable limit.
    """
    group_limits = IMPERFECTION_LIMIT_MM.get(imperfection.group)
    if group_limits is None:
        return ImperfectionResult(
            imperfection=imperfection,
            limit_mm=0.0,
            passed=False,
            note=f"Unrecognised imperfection group: {imperfection.group!r}",
        )
    limit = group_limits[weld_class]
    passed = imperfection.size_mm <= limit
    if passed:
        note = f"size {imperfection.size_mm} mm ≤ limit {limit} mm [OK]"
    else:
        note = f"REJECT: size {imperfection.size_mm} mm > limit {limit} mm"
    return ImperfectionResult(
        imperfection=imperfection,
        limit_mm=limit,
        passed=passed,
        note=note,
    )


def compute_fatigue_safe_life(
    applied_cycles: float,
    allowable_cycles: float,
    weld_class: WeldClass,
) -> FatigueResult:
    """
    Compute the safe-life factor = allowable_cycles / applied_cycles and
    compare it against the class requirement.
    Raises ValueError for non-positive cycle counts.
    """
    if applied_cycles <= 0.0:
        raise ValueError(
            f"applied_cycles must be positive; got {applied_cycles}"
        )
    if allowable_cycles <= 0.0:
        raise ValueError(
            f"allowable_cycles must be positive; got {allowable_cycles}"
        )
    usage = applied_cycles / allowable_cycles
    slf = allowable_cycles / applied_cycles
    required = REQUIRED_SAFE_LIFE_FACTOR[weld_class]
    passed = slf >= required
    if passed:
        note = f"SLF {slf:.3f} ≥ required {required:.1f} [OK]"
    else:
        note = f"FAIL: SLF {slf:.3f} < required {required:.1f}"
    return FatigueResult(
        usage_fraction=usage,
        safe_life_factor=slf,
        required_factor=required,
        passed=passed,
        note=note,
    )


def verify_ndt(
    ndt_methods: List[NdtMethod],
    coverage_fraction: float,
    assumed_initial_flaw_mm: float,
    weld_class: WeldClass,
) -> NdtResult:
    """
    Verify NDT adequacy:
    1. Coverage fraction meets the class requirement.
    2. Best detectable flaw size among applied methods <= assumed initial flaw.
    3. Class A welds must include at least one volumetric method.
    Raises ValueError for out-of-range coverage_fraction.
    """
    if not (0.0 <= coverage_fraction <= 1.0):
        raise ValueError(
            f"coverage_fraction must be in [0.0, 1.0]; got {coverage_fraction}"
        )
    if assumed_initial_flaw_mm <= 0.0:
        raise ValueError(
            f"assumed_initial_flaw_mm must be positive; got {assumed_initial_flaw_mm}"
        )

    required_cov = REQUIRED_NDT_COVERAGE[weld_class]
    coverage_passed = coverage_fraction >= required_cov

    if not ndt_methods:
        return NdtResult(
            coverage_passed=coverage_passed,
            flaw_detection_passed=False,
            has_volumetric=False,
            min_detectable_mm=float("inf"),
            required_coverage=required_cov,
            note="No NDT methods specified — flaw detection unverifiable",
        )

    min_detectable = min(NDT_MIN_DETECTABLE_MM[m] for m in ndt_methods)
    has_volumetric = bool(set(ndt_methods) & VOLUMETRIC_METHODS)
    flaw_detection_passed = min_detectable <= assumed_initial_flaw_mm

    # Class A requires volumetric inspection
    if weld_class == WeldClass.A and not has_volumetric:
        flaw_detection_passed = False

    notes: List[str] = []
    if not coverage_passed:
        notes.append(
            f"coverage {coverage_fraction:.0%} < required {required_cov:.0%}"
        )
    if weld_class == WeldClass.A and not has_volumetric:
        notes.append("Class A requires volumetric NDT (UT or RT)")
    elif not flaw_detection_passed:
        notes.append(
            f"min-detectable {min_detectable} mm > assumed flaw {assumed_initial_flaw_mm} mm"
        )
    if not notes:
        notes.append(
            f"coverage {coverage_fraction:.0%} OK; "
            f"min-detectable {min_detectable} mm ≤ flaw {assumed_initial_flaw_mm} mm [OK]"
        )

    return NdtResult(
        coverage_passed=coverage_passed,
        flaw_detection_passed=flaw_detection_passed,
        has_volumetric=has_volumetric,
        min_detectable_mm=min_detectable,
        required_coverage=required_cov,
        note="; ".join(notes),
    )


def assess_weld(assessment: WeldAssessment) -> WeldAssessmentResult:
    """
    Run the full ECSS-E-ST-32C clause 8.3 weld fracture-control assessment:
    screen imperfections, compute safe-life factor, verify NDT, aggregate findings.
    """
    findings: List[str] = []
    compliant = True

    # Step 1 — imperfection screening
    imp_results: List[ImperfectionResult] = []
    for imp in assessment.imperfections:
        r = screen_imperfection(imp, assessment.weld_class)
        imp_results.append(r)
        if not r.passed:
            findings.append(
                f"Imperfection {imp.group.name} @ {imp.location}: {r.note}"
            )
            compliant = False

    # Step 2 — safe-life fatigue
    fatigue_result: Optional[FatigueResult] = None
    if (
        assessment.applied_cycles is not None
        and assessment.allowable_cycles is not None
    ):
        fatigue_result = compute_fatigue_safe_life(
            assessment.applied_cycles,
            assessment.allowable_cycles,
            assessment.weld_class,
        )
        if not fatigue_result.passed:
            findings.append(f"Fatigue: {fatigue_result.note}")
            compliant = False
    else:
        findings.append("Fatigue inputs not provided — safe-life not assessed")

    # Step 3 — NDT
    ndt_result: Optional[NdtResult] = None
    if (
        assessment.assumed_initial_flaw_mm is not None
        and assessment.ndt_methods
    ):
        ndt_result = verify_ndt(
            assessment.ndt_methods,
            assessment.ndt_coverage_fraction,
            assessment.assumed_initial_flaw_mm,
            assessment.weld_class,
        )
        if not ndt_result.coverage_passed or not ndt_result.flaw_detection_passed:
            findings.append(f"NDT: {ndt_result.note}")
            compliant = False
    elif assessment.weld_class == WeldClass.A:
        findings.append(
            "Class A weld: NDT method or assumed initial flaw size not specified"
        )
        compliant = False

    return WeldAssessmentResult(
        weld_id=assessment.weld_id,
        weld_class=assessment.weld_class,
        imperfection_results=imp_results,
        fatigue_result=fatigue_result,
        ndt_result=ndt_result,
        compliant=compliant,
        findings=findings,
    )
