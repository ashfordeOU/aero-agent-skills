"""
e1011_verif_analysis_logic.py

HFE verification by analysis and similarity — ECSS-E-ST-10-11 §4.11.2.

Implements deterministic, offline logic for:
  - analysis method selection and validation
  - heritage similarity scoring across four required dimensions
  - DHM simulation result checking (joint angle, reach, force, visual field)
  - Annex B report completeness verification
  - findings aggregation

stdlib only. No external dependencies.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_ANALYSIS_METHODS: frozenset[str] = frozenset({
    "task_analysis",
    "cognitive_workload",
    "workspace_envelope",
    "anthropometric",
    "dhm_simulation",
    "similarity",
})

# Similarity dimensions that must each be scored for a heritage claim.
SIMILARITY_DIMENSIONS: tuple[str, ...] = (
    "function",
    "physical_form",
    "environment",
    "user_population",
)

# Composite score at or above this value grants heritage credit.
SIMILARITY_PASS_THRESHOLD: float = 0.80

# DHM acceptance limits.
DHM_JOINT_ANGLE_MAX_DEG: float = 30.0   # max deviation from neutral posture
DHM_FORCE_MAX_N: float = 200.0           # max required crew force (N)
DHM_VISUAL_ANGLE_MAX_DEG: float = 45.0  # max off-axis viewing angle (deg)

# Annex B core fields required in every analysis/simulation report.
ANNEX_B_CORE_FIELDS: frozenset[str] = frozenset({
    "analysis_id",
    "method",
    "scope",
    "crew_percentiles_used",
    "scenario_description",
    "results_summary",
    "findings",
    "recommendation",
})

# Extra required fields per analysis method.
ANNEX_B_EXTRA_FIELDS: dict[str, frozenset[str]] = {
    "similarity": frozenset({"heritage_reference"}),
    "dhm_simulation": frozenset({"dhm_software"}),
}

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalysisMethod:
    method_type: str
    description: str


@dataclass(frozen=True)
class DimensionScore:
    dimension: str
    score: float  # normalised [0.0, 1.0]


@dataclass(frozen=True)
class SimilarityClaim:
    heritage_id: str
    target_id: str
    dimension_scores: tuple[DimensionScore, ...]


@dataclass(frozen=True)
class DHMResult:
    scenario_id: str
    joint_angle_max_deviation_deg: float
    reach_zone_compliant: bool
    max_force_n: float
    visual_angle_max_deg: float


@dataclass(frozen=True)
class AnalysisReport:
    fields: dict  # field_name -> non-empty value


@dataclass(frozen=True)
class Finding:
    item_id: str
    severity: str   # "pass" | "warn" | "fail"
    detail: str


# ---------------------------------------------------------------------------
# Analysis method selection
# ---------------------------------------------------------------------------


_METHOD_DESCRIPTIONS: dict[str, str] = {
    "task_analysis": (
        "Structured decomposition of crew tasks into steps, durations, "
        "and sequences to assess time, error, and workload properties"
    ),
    "cognitive_workload": (
        "Assessment of crew cognitive load using a validated rating instrument "
        "such as NASA-TLX; output is a workload index per task phase"
    ),
    "workspace_envelope": (
        "Geometric verification that all crew interaction points fall within "
        "the reach and clearance envelope defined for the target percentile range"
    ),
    "anthropometric": (
        "Comparison of design dimensions against the crew body-dimension "
        "percentile ranges to confirm fit, clearance, and posture acceptability"
    ),
    "dhm_simulation": (
        "Three-dimensional digital human model simulation reproducing crew "
        "posture and interaction with hardware; yields joint angles, forces, "
        "reach compliance, and visual field metrics"
    ),
    "similarity": (
        "Heritage credit claim based on a scored comparison of function, "
        "physical form, operating environment, and user population against "
        "a previously verified reference design"
    ),
}


def select_analysis_method(method_type: str) -> AnalysisMethod:
    """Return a validated AnalysisMethod for the given type string.

    Raises ValueError for any type not in VALID_ANALYSIS_METHODS.
    """
    if method_type not in VALID_ANALYSIS_METHODS:
        raise ValueError(
            f"Unknown analysis method '{method_type}'. "
            f"Valid methods: {sorted(VALID_ANALYSIS_METHODS)}"
        )
    return AnalysisMethod(
        method_type=method_type,
        description=_METHOD_DESCRIPTIONS[method_type],
    )


# ---------------------------------------------------------------------------
# Heritage similarity scoring
# ---------------------------------------------------------------------------


def score_similarity(claim: SimilarityClaim) -> tuple[float, list[Finding]]:
    """Compute a composite similarity score for a heritage claim.

    Returns (composite_score, findings).
    composite_score >= SIMILARITY_PASS_THRESHOLD grants heritage credit.

    Raises ValueError if any dimension is unrecognised, any score is outside
    [0.0, 1.0], or a required dimension is absent from the claim.
    """
    findings: list[Finding] = []
    pair_id = f"{claim.heritage_id}->{claim.target_id}"

    seen_dims: dict[str, float] = {}
    for ds in claim.dimension_scores:
        if ds.dimension not in SIMILARITY_DIMENSIONS:
            raise ValueError(
                f"Unrecognised similarity dimension '{ds.dimension}'. "
                f"Required dimensions: {list(SIMILARITY_DIMENSIONS)}"
            )
        if not (0.0 <= ds.score <= 1.0):
            raise ValueError(
                f"Score for dimension '{ds.dimension}' must be in [0.0, 1.0], "
                f"got {ds.score}"
            )
        seen_dims[ds.dimension] = ds.score

    missing = [d for d in SIMILARITY_DIMENSIONS if d not in seen_dims]
    if missing:
        raise ValueError(
            f"Similarity claim missing required dimensions: {missing}"
        )

    composite = sum(seen_dims[d] for d in SIMILARITY_DIMENSIONS) / len(SIMILARITY_DIMENSIONS)

    for dim, score in seen_dims.items():
        severity = "pass" if score >= SIMILARITY_PASS_THRESHOLD else "fail"
        findings.append(Finding(
            item_id=f"{pair_id}.{dim}",
            severity=severity,
            detail=(
                f"Dimension '{dim}': score {score:.3f} "
                + ("passes" if severity == "pass" else
                   f"is below threshold {SIMILARITY_PASS_THRESHOLD} — supplementary analysis required")
            ),
        ))

    overall_severity = "pass" if composite >= SIMILARITY_PASS_THRESHOLD else "fail"
    findings.append(Finding(
        item_id=f"{pair_id}.composite",
        severity=overall_severity,
        detail=(
            f"Composite similarity score {composite:.3f} "
            + ("≥" if composite >= SIMILARITY_PASS_THRESHOLD else "<")
            + f" {SIMILARITY_PASS_THRESHOLD}: heritage credit "
            + ("granted" if overall_severity == "pass" else "denied")
        ),
    ))

    return composite, findings


# ---------------------------------------------------------------------------
# DHM simulation result checking
# ---------------------------------------------------------------------------


def check_dhm_result(result: DHMResult) -> list[Finding]:
    """Evaluate a DHM simulation result against the four acceptance criteria.

    Returns one Finding per criterion (joint_angle, reach_zone, force,
    visual_angle). Each is independently pass or fail.
    """
    findings: list[Finding] = []
    sid = result.scenario_id

    # 1. Joint angle deviation
    if result.joint_angle_max_deviation_deg <= DHM_JOINT_ANGLE_MAX_DEG:
        findings.append(Finding(
            item_id=f"{sid}.joint_angle",
            severity="pass",
            detail=(
                f"Joint angle deviation {result.joint_angle_max_deviation_deg:.1f}° "
                f"≤ limit {DHM_JOINT_ANGLE_MAX_DEG:.0f}°"
            ),
        ))
    else:
        findings.append(Finding(
            item_id=f"{sid}.joint_angle",
            severity="fail",
            detail=(
                f"Joint angle deviation {result.joint_angle_max_deviation_deg:.1f}° "
                f"exceeds limit {DHM_JOINT_ANGLE_MAX_DEG:.0f}° — "
                "redesign hardware position or add adjustment range"
            ),
        ))

    # 2. Reach zone compliance
    if result.reach_zone_compliant:
        findings.append(Finding(
            item_id=f"{sid}.reach_zone",
            severity="pass",
            detail="All crew interaction points within reach envelope",
        ))
    else:
        findings.append(Finding(
            item_id=f"{sid}.reach_zone",
            severity="fail",
            detail=(
                "One or more interaction points fall outside the crew reach envelope — "
                "reposition hardware or verify with alternative crew percentile"
            ),
        ))

    # 3. Required force
    if result.max_force_n <= DHM_FORCE_MAX_N:
        findings.append(Finding(
            item_id=f"{sid}.force",
            severity="pass",
            detail=(
                f"Maximum crew force {result.max_force_n:.1f} N "
                f"≤ limit {DHM_FORCE_MAX_N:.0f} N"
            ),
        ))
    else:
        findings.append(Finding(
            item_id=f"{sid}.force",
            severity="fail",
            detail=(
                f"Maximum crew force {result.max_force_n:.1f} N "
                f"exceeds limit {DHM_FORCE_MAX_N:.0f} N — "
                "reduce required force or introduce mechanical advantage"
            ),
        ))

    # 4. Visual field (off-axis angle)
    if result.visual_angle_max_deg <= DHM_VISUAL_ANGLE_MAX_DEG:
        findings.append(Finding(
            item_id=f"{sid}.visual_angle",
            severity="pass",
            detail=(
                f"Off-axis viewing angle {result.visual_angle_max_deg:.1f}° "
                f"≤ limit {DHM_VISUAL_ANGLE_MAX_DEG:.0f}°"
            ),
        ))
    else:
        findings.append(Finding(
            item_id=f"{sid}.visual_angle",
            severity="fail",
            detail=(
                f"Off-axis viewing angle {result.visual_angle_max_deg:.1f}° "
                f"exceeds limit {DHM_VISUAL_ANGLE_MAX_DEG:.0f}° — "
                "reposition display or rotate workstation to bring display into primary visual cone"
            ),
        ))

    return findings


# ---------------------------------------------------------------------------
# Annex B report completeness
# ---------------------------------------------------------------------------


def check_report_completeness(report: AnalysisReport, method: str) -> list[Finding]:
    """Verify that an analysis/simulation report contains all Annex B fields.

    Core fields are required for every report.
    Additional method-specific fields apply for 'similarity' and 'dhm_simulation'.

    Raises ValueError for an unrecognised method type.
    """
    if method not in VALID_ANALYSIS_METHODS:
        raise ValueError(
            f"Unknown method '{method}'. Valid methods: {sorted(VALID_ANALYSIS_METHODS)}"
        )

    findings: list[Finding] = []
    required = set(ANNEX_B_CORE_FIELDS)
    required |= ANNEX_B_EXTRA_FIELDS.get(method, frozenset())

    present = set(report.fields.keys())
    report_id = report.fields.get("analysis_id", "<unknown>")

    for field_name in sorted(required - present):
        findings.append(Finding(
            item_id=f"report.{report_id}.{field_name}",
            severity="fail",
            detail=f"Annex B required field '{field_name}' is absent from report '{report_id}'",
        ))

    if not (required - present):
        findings.append(Finding(
            item_id=f"report.{report_id}",
            severity="pass",
            detail=f"Report '{report_id}' contains all required Annex B fields for method '{method}'",
        ))

    return findings


# ---------------------------------------------------------------------------
# Findings aggregation
# ---------------------------------------------------------------------------


def aggregate_findings(findings: list[Finding]) -> dict:
    """Aggregate a list of findings into an overall verification status.

    Returns a dict with keys:
        status      — "pass" if no fail findings, otherwise "fail"
        fail_count  — number of fail-severity findings
        warn_count  — number of warn-severity findings
        pass_count  — number of pass-severity findings
        total       — total finding count
    """
    fail_count = sum(1 for f in findings if f.severity == "fail")
    warn_count = sum(1 for f in findings if f.severity == "warn")
    pass_count = sum(1 for f in findings if f.severity == "pass")
    return {
        "status": "fail" if fail_count > 0 else "pass",
        "fail_count": fail_count,
        "warn_count": warn_count,
        "pass_count": pass_count,
        "total": len(findings),
    }
