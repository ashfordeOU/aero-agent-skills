"""
EEE Component Radiation Susceptibility Uncertainty — Margin Sizing Logic
Anchor: ECSS-E-ST-10-12C §5.5.1
Deterministic, stdlib-only, offline.
"""

from __future__ import annotations

EFFECT_TYPES: frozenset[str] = frozenset({"TID", "SEE", "NIEL", "DD"})
SOURCE_TYPES: frozenset[str] = frozenset(
    {"space_flight", "ground_equivalent", "vendor_spec", "assumed"}
)

# Uncertainty factor keyed by data quality level.
# Applied on top of the base RDM to cover the unknown portion of the
# component distribution when test data are limited.
_UNCERTAINTY_FACTORS: dict[str, float] = {
    "high":   1.0,
    "medium": 1.5,
    "low":    2.0,
    "absent": 3.0,
}

_LEVEL_DESCRIPTIONS: dict[str, str] = {
    "high":   "Well-characterized: 2+ lots, 5+ samples, qualified test source",
    "medium": "Limited data: single lot, <5 samples, or non-standard test source",
    "low":    "Sparse data: single test point or vendor specification only",
    "absent": "No test data: worst-case assumption required",
}


def categorize_data_quality(
    sample_size: int,
    source_type: str,
    lot_count: int = 1,
) -> dict:
    """
    Categorize the uncertainty level of radiation susceptibility data for one
    component / effect-type pair.

    Parameters
    ----------
    sample_size : number of individually tested components (0 = no data)
    source_type : one of 'space_flight', 'ground_equivalent', 'vendor_spec', 'assumed'
    lot_count   : number of distinct manufacturing lots represented (>=1)

    Returns
    -------
    dict with keys: level (str), uncertainty_factor (float), description (str)
    """
    if not isinstance(sample_size, int) or sample_size < 0:
        raise ValueError(
            f"sample_size must be a non-negative integer; got {sample_size!r}"
        )
    if source_type not in SOURCE_TYPES:
        raise ValueError(
            f"source_type must be one of {sorted(SOURCE_TYPES)}; got {source_type!r}"
        )
    if not isinstance(lot_count, int) or lot_count < 1:
        raise ValueError(
            f"lot_count must be a positive integer; got {lot_count!r}"
        )

    if sample_size == 0 or source_type == "assumed":
        level = "absent"
    elif (
        sample_size >= 5
        and source_type in ("space_flight", "ground_equivalent")
        and lot_count >= 2
    ):
        level = "high"
    elif sample_size >= 3 or source_type in ("space_flight", "ground_equivalent"):
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "uncertainty_factor": _UNCERTAINTY_FACTORS[level],
        "description": _LEVEL_DESCRIPTIONS[level],
    }


def compute_required_threshold(
    environment_dose: float,
    base_rdm: float,
    uncertainty_factor: float,
) -> float:
    """
    Compute the minimum component susceptibility threshold required to satisfy
    the uncertainty-adjusted margin.

    required_threshold = environment_dose * base_rdm * uncertainty_factor

    Parameters
    ----------
    environment_dose   : worst-case shielded environment value (rad, krad, etc.)
    base_rdm           : base radiation design margin (>=1.0; typically 2.0 for TID)
    uncertainty_factor : data-quality multiplier from categorize_data_quality

    Returns
    -------
    float : minimum required component threshold in the same units as environment_dose
    """
    if environment_dose <= 0:
        raise ValueError(f"environment_dose must be positive; got {environment_dose}")
    if base_rdm < 1.0:
        raise ValueError(f"base_rdm must be >= 1.0; got {base_rdm}")
    if uncertainty_factor < 1.0:
        raise ValueError(
            f"uncertainty_factor must be >= 1.0; got {uncertainty_factor}"
        )
    return environment_dose * base_rdm * uncertainty_factor


def check_component_margin(
    component_threshold: float,
    environment_dose: float,
    base_rdm: float,
    uncertainty_factor: float,
) -> dict:
    """
    Check whether a component's susceptibility threshold satisfies the
    uncertainty-adjusted margin requirement.

    Returns
    -------
    dict with keys:
        passes                (bool)
        required_threshold    (float)  environment_dose * base_rdm * uncertainty_factor
        achieved_rdm          (float)  component_threshold / environment_dose
        effective_required_rdm (float) base_rdm * uncertainty_factor
        shortfall             (float | None)  gap when failing, else None
    """
    if component_threshold <= 0:
        raise ValueError(
            f"component_threshold must be positive; got {component_threshold}"
        )
    required = compute_required_threshold(environment_dose, base_rdm, uncertainty_factor)
    passes = component_threshold >= required
    return {
        "passes": passes,
        "required_threshold": required,
        "achieved_rdm": component_threshold / environment_dose,
        "effective_required_rdm": base_rdm * uncertainty_factor,
        "shortfall": None if passes else required - component_threshold,
    }


def assess_component(
    component_id: str,
    effect_type: str,
    component_threshold: float,
    environment_dose: float,
    base_rdm: float,
    sample_size: int,
    source_type: str,
    lot_count: int = 1,
) -> dict:
    """
    Full pipeline for one component / effect-type pair:
    categorize data quality -> derive uncertainty factor ->
    compute required threshold -> check margin.
    """
    if effect_type not in EFFECT_TYPES:
        raise ValueError(
            f"effect_type must be one of {sorted(EFFECT_TYPES)}; got {effect_type!r}"
        )
    quality = categorize_data_quality(sample_size, source_type, lot_count)
    margin = check_component_margin(
        component_threshold, environment_dose, base_rdm, quality["uncertainty_factor"]
    )
    return {
        "component_id": component_id,
        "effect_type": effect_type,
        "data_quality": quality,
        **margin,
    }


def assess_batch(components: list[dict]) -> list[dict]:
    """
    Assess a list of component records. Each dict must carry the same keyword
    arguments accepted by assess_component. Returns a result list in the same
    order as the input.
    """
    return [assess_component(**c) for c in components]
