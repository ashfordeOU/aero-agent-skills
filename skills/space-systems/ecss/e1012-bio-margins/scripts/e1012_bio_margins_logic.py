"""
Biological effects margin logic for crewed missions.
Anchor: ECSS-E-ST-10C §5.5.5 — margin philosophy for biological effects.

All stressor exposures are expressed in mission-consistent physical units
(e.g. mSv for radiation dose, Pa for pressure, dB for acoustic).
Margin factors are dimensionless multipliers applied to design-point exposures.
"""

from dataclasses import dataclass
from typing import List, Optional

# ── Stressor categories ────────────────────────────────────────────────────────
RADIATION = "radiation"
PHYSIOLOGICAL = "physiological"
ATMOSPHERIC = "atmospheric"
THERMAL = "thermal"
ACOUSTIC = "acoustic"

VALID_STRESSOR_TYPES = frozenset(
    {RADIATION, PHYSIOLOGICAL, ATMOSPHERIC, THERMAL, ACOUSTIC}
)

# ── Margin factors (ECSS-E-ST-10C §5.5.5) ─────────────────────────────────────
# Radiation (ionizing) uses a higher margin to bound the greater model
# uncertainty in biological dose–response relationships.
# All other biological stressors use the standard 25 % design margin.
MARGIN_FACTORS = {
    RADIATION: 1.5,
    PHYSIOLOGICAL: 1.25,
    ATMOSPHERIC: 1.25,
    THERMAL: 1.25,
    ACOUSTIC: 1.25,
}

# ── Finding status codes ───────────────────────────────────────────────────────
COMPLIANT = "COMPLIANT"
EXCEEDANCE = "EXCEEDANCE"
LIMIT_UNSET = "LIMIT_UNSET"
INVALID_STRESSOR = "INVALID_STRESSOR"


@dataclass(frozen=True)
class Stressor:
    """A single biological stressor with its design-point exposure and limit."""
    name: str
    stressor_type: str
    design_exposure: float       # design-point value before margin application
    allowable_limit: Optional[float]  # crew health requirement; None if unset


@dataclass(frozen=True)
class Finding:
    """Margin assessment result for one stressor."""
    stressor_name: str
    stressor_type: str
    design_exposure: float
    margin_factor: float
    margined_exposure: float
    allowable_limit: Optional[float]
    status: str
    detail: str


def get_margin_factor(stressor_type: str) -> float:
    """Return the margin factor for a stressor type.

    Raises ValueError for an unrecognized type so callers fail explicitly
    rather than silently using a wrong factor.
    """
    if stressor_type not in VALID_STRESSOR_TYPES:
        raise ValueError(
            f"Unrecognized stressor type {stressor_type!r}. "
            f"Valid types: {sorted(VALID_STRESSOR_TYPES)}"
        )
    return MARGIN_FACTORS[stressor_type]


def apply_margin(design_exposure: float, margin_factor: float) -> float:
    """Multiply design exposure by the margin factor.

    Both inputs must be non-negative / >= 1.0 respectively; any other value
    indicates a data error upstream.
    """
    if design_exposure < 0.0:
        raise ValueError(
            f"design_exposure must be non-negative; received {design_exposure}"
        )
    if margin_factor < 1.0:
        raise ValueError(
            f"margin_factor must be >= 1.0; received {margin_factor}"
        )
    return design_exposure * margin_factor


def assess_stressor(stressor: Stressor) -> Finding:
    """Assess one stressor: apply margin and compare against the allowable limit.

    Returns a Finding whose status is one of COMPLIANT, EXCEEDANCE,
    LIMIT_UNSET, or INVALID_STRESSOR.
    """
    if stressor.stressor_type not in VALID_STRESSOR_TYPES:
        return Finding(
            stressor_name=stressor.name,
            stressor_type=stressor.stressor_type,
            design_exposure=stressor.design_exposure,
            margin_factor=0.0,
            margined_exposure=0.0,
            allowable_limit=stressor.allowable_limit,
            status=INVALID_STRESSOR,
            detail=(
                f"Stressor type {stressor.stressor_type!r} is not recognized; "
                "stressor must be categorized before margin assessment."
            ),
        )

    margin_factor = get_margin_factor(stressor.stressor_type)
    margined_exposure = apply_margin(stressor.design_exposure, margin_factor)

    if stressor.allowable_limit is None:
        return Finding(
            stressor_name=stressor.name,
            stressor_type=stressor.stressor_type,
            design_exposure=stressor.design_exposure,
            margin_factor=margin_factor,
            margined_exposure=margined_exposure,
            allowable_limit=None,
            status=LIMIT_UNSET,
            detail=(
                "No crew health allowable limit is on record for this stressor; "
                "compliance cannot be determined until the limit is set."
            ),
        )

    if margined_exposure > stressor.allowable_limit:
        return Finding(
            stressor_name=stressor.name,
            stressor_type=stressor.stressor_type,
            design_exposure=stressor.design_exposure,
            margin_factor=margin_factor,
            margined_exposure=margined_exposure,
            allowable_limit=stressor.allowable_limit,
            status=EXCEEDANCE,
            detail=(
                f"Margined exposure {margined_exposure:.4g} exceeds "
                f"allowable limit {stressor.allowable_limit:.4g}."
            ),
        )

    return Finding(
        stressor_name=stressor.name,
        stressor_type=stressor.stressor_type,
        design_exposure=stressor.design_exposure,
        margin_factor=margin_factor,
        margined_exposure=margined_exposure,
        allowable_limit=stressor.allowable_limit,
        status=COMPLIANT,
        detail="Margined exposure is within the crew health allowable limit.",
    )


def assess_bio_margins(stressors: List[Stressor]) -> List[Finding]:
    """Return one Finding per Stressor, preserving input order."""
    return [assess_stressor(s) for s in stressors]


def is_mission_compliant(findings: List[Finding]) -> bool:
    """Return True only when every finding has status COMPLIANT."""
    return all(f.status == COMPLIANT for f in findings)


def summarize_findings(findings: List[Finding]) -> dict:
    """Return a count of findings grouped by status."""
    summary: dict = {COMPLIANT: 0, EXCEEDANCE: 0, LIMIT_UNSET: 0, INVALID_STRESSOR: 0}
    for f in findings:
        if f.status in summary:
            summary[f.status] += 1
        else:
            summary[f.status] = 1
    return summary
