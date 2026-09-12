"""
Fracture material selection screening — ECSS-Q-ST-70-36.
Implements the material acceptance screening procedure (clause 5 / 6).
All ECSS text is paraphrased; cite Q-ST-70-36 as the normative anchor.
stdlib only — no third-party dependencies.
"""

from dataclasses import dataclass, field
from typing import Optional, List


# ---------------------------------------------------------------------------
# Constants — derived from Q-ST-70-36 procedure (paraphrased)
# ---------------------------------------------------------------------------

MIN_KIC_FRACTURE_CRITICAL_MPAsqrtm = 22.0  # minimum KIc for fracture-critical parts

SCC_RATIO_LIMIT_REJECT = 0.10       # KIscc/KIc below this → reject
SCC_RATIO_LIMIT_CONDITIONAL = 0.25  # KIscc/KIc below this (and >= reject limit) → conditional

VALID_SCC_CODES = {"A", "B", "C", "D"}

# Environments that introduce aqueous/chemical SCC exposure
_CORROSIVE_ENVS = {"moist", "propellant", "aqueous"}
# Most aggressive subset — triggers even code-B conditional
_SEVERE_ENVS = {"propellant", "aqueous"}

VALID_ENVIRONMENTS = {"dry", "moist", "propellant", "aqueous"}


# ---------------------------------------------------------------------------
# Input / output types
# ---------------------------------------------------------------------------

@dataclass
class MaterialCandidate:
    """Input record for one material under fracture-control screening."""
    name: str
    scc_code: str                        # "A", "B", "C", or "D"
    kic_mpa_sqrtm: float                 # plane-strain fracture toughness (MPa√m)
    kiscc_mpa_sqrtm: Optional[float]     # SCC threshold toughness; None when code is "A" or data unavailable
    is_fracture_critical: bool           # True → part is fracture-critical per fracture-control plan
    environment: str                     # "dry" | "moist" | "propellant" | "aqueous"
    on_prohibited_list: bool = False     # appears on Q-ST-70-36 Appendix A prohibited list


@dataclass
class ScreeningResult:
    """Screening outcome for a single material candidate."""
    name: str
    verdict: str                         # "ACCEPT" | "CONDITIONAL" | "REJECT"
    scc_ratio: Optional[float]           # kiscc / kic, or None when kiscc not provided
    findings: List[str]                  # human-readable finding strings


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validate(mc: MaterialCandidate) -> List[str]:
    errors: List[str] = []
    if not mc.name or not mc.name.strip():
        errors.append("material name must not be empty")
    if mc.scc_code not in VALID_SCC_CODES:
        errors.append(
            f"scc_code '{mc.scc_code}' is not valid; expected one of {sorted(VALID_SCC_CODES)}"
        )
    if mc.kic_mpa_sqrtm <= 0:
        errors.append("kic_mpa_sqrtm must be a positive number")
    if mc.kiscc_mpa_sqrtm is not None and mc.kiscc_mpa_sqrtm < 0:
        errors.append("kiscc_mpa_sqrtm must be non-negative when provided")
    if mc.environment not in VALID_ENVIRONMENTS:
        errors.append(
            f"environment '{mc.environment}' is not valid; "
            f"expected one of {sorted(VALID_ENVIRONMENTS)}"
        )
    return errors


# ---------------------------------------------------------------------------
# Core screening function
# ---------------------------------------------------------------------------

def screen_material(mc: MaterialCandidate) -> ScreeningResult:
    """
    Screen a material candidate for fracture-control acceptability per Q-ST-70-36.

    Verdict logic (highest severity wins):
      REJECT      — prohibited list | KIc below floor for fracture-critical |
                    KIscc/KIc < 0.10 | SCC code D in corrosive env |
                    KIscc missing for susceptible material in corrosive env
      CONDITIONAL — KIscc/KIc in [0.10, 0.25) | SCC code C in corrosive env |
                    SCC code B in propellant/aqueous env
      ACCEPT      — all checks clear

    Raises ValueError for invalid input.
    """
    errors = _validate(mc)
    if errors:
        raise ValueError(
            f"Invalid MaterialCandidate '{mc.name}': {'; '.join(errors)}"
        )

    findings: List[str] = []
    reject = False
    conditional = False

    # Step 1 — prohibited materials list (Q-ST-70-36 App. A)
    if mc.on_prohibited_list:
        findings.append(
            "REJECT: material on prohibited list (Q-ST-70-36 App. A)"
        )
        return ScreeningResult(
            name=mc.name, verdict="REJECT", scc_ratio=None, findings=findings
        )

    # Step 2 — minimum KIc for fracture-critical parts (Q-ST-70-36 clause 5)
    if mc.is_fracture_critical and mc.kic_mpa_sqrtm < MIN_KIC_FRACTURE_CRITICAL_MPAsqrtm:
        findings.append(
            f"REJECT: KIc {mc.kic_mpa_sqrtm:.1f} MPa√m is below the "
            f"{MIN_KIC_FRACTURE_CRITICAL_MPAsqrtm:.0f} MPa√m minimum for "
            f"fracture-critical parts (Q-ST-70-36 clause 5)"
        )
        reject = True

    # Step 3 — KIscc/KIc ratio check (Q-ST-70-36 clause 6.2)
    scc_ratio: Optional[float] = None
    if mc.kiscc_mpa_sqrtm is not None:
        scc_ratio = mc.kiscc_mpa_sqrtm / mc.kic_mpa_sqrtm
        if scc_ratio < SCC_RATIO_LIMIT_REJECT:
            findings.append(
                f"REJECT: KIscc/KIc = {scc_ratio:.3f} is below {SCC_RATIO_LIMIT_REJECT} — "
                f"material cannot sustain a safe threshold stress around a crack in service "
                f"(Q-ST-70-36 clause 6.2)"
            )
            reject = True
        elif scc_ratio < SCC_RATIO_LIMIT_CONDITIONAL:
            findings.append(
                f"CONDITIONAL: KIscc/KIc = {scc_ratio:.3f} is in the range "
                f"[{SCC_RATIO_LIMIT_REJECT}, {SCC_RATIO_LIMIT_CONDITIONAL}) — design stress "
                f"must not exceed the KIscc-derived allowable and sustained-load SCC test "
                f"data are required (Q-ST-70-36 clause 6.2)"
            )
            conditional = True

    # Step 4 — SCC code vs service environment (Q-ST-70-36 clause 6.3)
    if mc.environment in _CORROSIVE_ENVS:
        if mc.scc_code == "D":
            findings.append(
                f"REJECT: SCC code D (high susceptibility) is not permitted in a "
                f"{mc.environment} environment (Q-ST-70-36 clause 6.3)"
            )
            reject = True
        elif mc.scc_code == "C":
            findings.append(
                f"CONDITIONAL: SCC code C (moderate susceptibility) in a {mc.environment} "
                f"environment — design stress must not exceed 75 % Fty and SCC qualification "
                f"test data must be on record (Q-ST-70-36 clause 6.3)"
            )
            conditional = True
        elif mc.scc_code == "B" and mc.environment in _SEVERE_ENVS:
            findings.append(
                f"CONDITIONAL: SCC code B (low susceptibility) in a {mc.environment} "
                f"environment — sustained-stress SCC confirmation testing is required "
                f"(Q-ST-70-36 clause 6.3)"
            )
            conditional = True
    else:
        # dry environment: note absent KIscc for susceptible codes so risk is flagged
        # if the environment ever changes
        if mc.scc_code != "A" and mc.kiscc_mpa_sqrtm is None:
            findings.append(
                f"NOTE: SCC code {mc.scc_code} with no KIscc provided — acceptable for a "
                f"dry environment; re-evaluate if the service environment changes"
            )

    # Step 5 — missing KIscc for susceptible code in corrosive environment
    if (
        mc.scc_code in ("B", "C", "D")
        and mc.environment in _CORROSIVE_ENVS
        and mc.kiscc_mpa_sqrtm is None
    ):
        findings.append(
            f"REJECT: KIscc not provided for SCC code {mc.scc_code} material in a "
            f"{mc.environment} environment — fracture-control margin cannot be verified "
            f"(Q-ST-70-36 clause 6.2)"
        )
        reject = True

    # Determine verdict
    if reject:
        verdict = "REJECT"
    elif conditional:
        verdict = "CONDITIONAL"
    else:
        verdict = "ACCEPT"

    return ScreeningResult(
        name=mc.name, verdict=verdict, scc_ratio=scc_ratio, findings=findings
    )


# ---------------------------------------------------------------------------
# Batch helper
# ---------------------------------------------------------------------------

def screen_material_list(candidates: List[MaterialCandidate]) -> List[ScreeningResult]:
    """Screen a list of material candidates and return one result per candidate."""
    return [screen_material(c) for c in candidates]


# ---------------------------------------------------------------------------
# Summary helper
# ---------------------------------------------------------------------------

def summarize_screening(results: List[ScreeningResult]) -> dict:
    """Return counts of ACCEPT, CONDITIONAL, and REJECT from a batch of results."""
    summary: dict = {"ACCEPT": 0, "CONDITIONAL": 0, "REJECT": 0}
    for r in results:
        if r.verdict in summary:
            summary[r.verdict] += 1
    return summary
