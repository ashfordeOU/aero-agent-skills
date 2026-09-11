"""
ECSS-E-ST-10-12C §6.2.1 shielding calculation process — paraphrased logic.
Standard cited as anchor only; no verbatim ECSS text.
Stdlib only, offline, deterministic.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ─── Enumerations ─────────────────────────────────────────────────────────────

class EffectType(Enum):
    TID = "TID"                    # Total Ionizing Dose
    DD = "DD"                      # Displacement Damage (NIEL-weighted)
    SEE_PROTON = "SEE_proton"      # Single Event Effects — proton induced
    SEE_HEAVY_ION = "SEE_heavy_ion"  # Single Event Effects — heavy ion (LET)


class GeometryComplexity(Enum):
    SIMPLE = "simple"       # slab / spherical-shell approximation adequate
    MODERATE = "moderate"   # sector analysis (ray-trace integration)
    COMPLEX = "complex"     # Monte Carlo particle transport required


class CalculationMethod(Enum):
    SLAB_APPROX = "slab_approximation"
    SECTOR_ANALYSIS = "sector_analysis"
    MONTE_CARLO = "monte_carlo"
    NIEL_WEIGHTED = "niel_weighted_fluence"
    LET_SPECTRUM = "let_spectrum"


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class ShieldConfig:
    """Shielding configuration for a spacecraft component."""
    component_id: str
    primary_thickness_mm: float    # aluminium-equivalent primary shielding
    secondary_thickness_mm: float  # local spot shielding
    material: str                  # e.g. "aluminium", "tantalum"

    def __post_init__(self) -> None:
        if not self.component_id:
            raise ValueError("component_id must not be empty")
        if self.primary_thickness_mm < 0:
            raise ValueError(
                f"primary_thickness_mm must be >= 0, got {self.primary_thickness_mm}"
            )
        if self.secondary_thickness_mm < 0:
            raise ValueError(
                f"secondary_thickness_mm must be >= 0, got {self.secondary_thickness_mm}"
            )
        if not self.material:
            raise ValueError("material must not be empty")

    @property
    def total_thickness_mm(self) -> float:
        return self.primary_thickness_mm + self.secondary_thickness_mm


@dataclass
class RadiationRequirement:
    """Dose or fluence limit with radiation design margin for one component × effect."""
    component_id: str
    effect_type: EffectType
    limit: float          # dose limit (rad) or fluence limit (p/cm²)
    margin_factor: float  # radiation design margin (RDM), typically >= 2.0

    def __post_init__(self) -> None:
        if not self.component_id:
            raise ValueError("component_id must not be empty")
        if self.limit <= 0:
            raise ValueError(f"limit must be > 0, got {self.limit}")
        if self.margin_factor < 1.0:
            raise ValueError(
                f"margin_factor must be >= 1.0, got {self.margin_factor}"
            )

    @property
    def design_limit(self) -> float:
        """Effective limit after applying the radiation design margin."""
        return self.limit / self.margin_factor


@dataclass
class CalculationResult:
    """Outcome of the shielding calculation for one component × effect pair."""
    component_id: str
    effect_type: EffectType
    method: CalculationMethod
    predicted_dose: float
    limit: float
    margin_factor: float
    shielding_adequate: bool
    primary_contribution_mm: float
    secondary_contribution_mm: float
    notes: List[str] = field(default_factory=list)


# ─── Material attenuation database ───────────────────────────────────────────
# Half-value layer in mm for a simplified exponential shielding model.
# These are representative engineering estimates for the logic module;
# flight calculations use tabulated shielding curves from environment tools.

_HVL_MM: Dict[str, float] = {
    "aluminium": 5.0,
    "tantalum": 1.5,
    "polyethylene": 12.0,
    "titanium": 4.0,
    "steel": 3.5,
}


# ─── Method selection ─────────────────────────────────────────────────────────

def select_method(
    effect_type: EffectType,
    geometry: GeometryComplexity,
) -> CalculationMethod:
    """
    Select the shielding calculation method for a given radiation effect and
    geometry complexity, following the effect × geometry table of
    ECSS-E-ST-10-12C §6.2.1 (paraphrased).

    TID / proton-SEE: slab for simple, sector analysis for moderate,
    Monte Carlo for complex.
    DD: NIEL-weighted fluence for simple/moderate, Monte Carlo for complex.
    Heavy-ion SEE: LET-spectrum assessment regardless of geometry.
    """
    if effect_type == EffectType.SEE_HEAVY_ION:
        return CalculationMethod.LET_SPECTRUM

    if effect_type == EffectType.DD:
        if geometry == GeometryComplexity.COMPLEX:
            return CalculationMethod.MONTE_CARLO
        return CalculationMethod.NIEL_WEIGHTED

    # TID and SEE_PROTON share the same geometry-driven table
    if geometry == GeometryComplexity.SIMPLE:
        return CalculationMethod.SLAB_APPROX
    if geometry == GeometryComplexity.MODERATE:
        return CalculationMethod.SECTOR_ANALYSIS
    return CalculationMethod.MONTE_CARLO


# ─── Attenuation calculation ──────────────────────────────────────────────────

def attenuation_factor(material: str, thickness_mm: float) -> float:
    """
    Compute a dimensionless dose attenuation factor using a simplified
    half-value-layer exponential model.  For flight use, replace with
    shielding curves produced by sector-analysis or Monte Carlo tools.

    f = exp(-ln2 * thickness / HVL)
    """
    key = material.lower()
    if key not in _HVL_MM:
        raise ValueError(
            f"Unknown material '{material}'. Supported: {sorted(_HVL_MM)}"
        )
    if thickness_mm < 0:
        raise ValueError(f"thickness_mm must be >= 0, got {thickness_mm}")
    hvl = _HVL_MM[key]
    return math.exp(-math.log(2) * thickness_mm / hvl)


def compute_predicted_dose(
    unshielded_dose: float,
    config: ShieldConfig,
    effect_type: EffectType,
) -> float:
    """
    Estimate the dose or fluence at the component behind its combined primary
    and secondary shielding.

    Heavy-ion SEE: bulk shielding does not materially attenuate the LET
    spectrum at typical spacecraft thicknesses; return the unshielded value.
    All other effects: apply the exponential attenuation model over the total
    aluminium-equivalent thickness.
    """
    if unshielded_dose < 0:
        raise ValueError(f"unshielded_dose must be >= 0, got {unshielded_dose}")

    if effect_type == EffectType.SEE_HEAVY_ION:
        return unshielded_dose

    factor = attenuation_factor(config.material, config.total_thickness_mm)
    return unshielded_dose * factor


# ─── Adequacy check ───────────────────────────────────────────────────────────

def check_adequacy(
    predicted_dose: float,
    req: RadiationRequirement,
) -> Tuple[bool, List[str]]:
    """
    Return (adequate, notes).  Adequate when predicted_dose <= limit / RDM.
    The design limit (limit / RDM) is computed once and compared; a margin
    factor of 2 means the predicted value must not exceed half the stated limit.
    """
    design_lim = req.design_limit
    adequate = predicted_dose <= design_lim
    notes: List[str] = []
    if not adequate:
        shortfall = predicted_dose - design_lim
        notes.append(
            f"Predicted {predicted_dose:.4g} exceeds design limit {design_lim:.4g} "
            f"(= {req.limit:.4g} / RDM {req.margin_factor}) by {shortfall:.4g}"
        )
    return adequate, notes


# ─── Full process orchestration ───────────────────────────────────────────────

def run_shielding_process(
    unshielded_doses: Dict[Tuple[str, EffectType], float],
    shield_configs: Dict[str, ShieldConfig],
    requirements: List[RadiationRequirement],
    geometry: GeometryComplexity = GeometryComplexity.MODERATE,
) -> List[CalculationResult]:
    """
    Execute the ECSS-E-ST-10-12C §6.2.1 shielding calculation process across
    a set of components and effects.

    Parameters
    ----------
    unshielded_doses : mapping of (component_id, EffectType) → unshielded value
    shield_configs   : mapping of component_id → ShieldConfig
    requirements     : one RadiationRequirement per (component, effect) pair
    geometry         : overall geometry complexity (drives method selection)

    Returns
    -------
    List[CalculationResult] — one entry per requirement.

    Raises
    ------
    ValueError if a required config or unshielded dose entry is missing.
    """
    results: List[CalculationResult] = []

    for req in requirements:
        cid = req.component_id
        et = req.effect_type

        config = shield_configs.get(cid)
        if config is None:
            raise ValueError(f"No ShieldConfig for component '{cid}'")

        key = (cid, et)
        if key not in unshielded_doses:
            raise ValueError(
                f"No unshielded dose for ({cid}, {et.value})"
            )
        unshielded = unshielded_doses[key]

        method = select_method(et, geometry)
        predicted = compute_predicted_dose(unshielded, config, et)
        adequate, notes = check_adequacy(predicted, req)

        results.append(CalculationResult(
            component_id=cid,
            effect_type=et,
            method=method,
            predicted_dose=predicted,
            limit=req.limit,
            margin_factor=req.margin_factor,
            shielding_adequate=adequate,
            primary_contribution_mm=config.primary_thickness_mm,
            secondary_contribution_mm=config.secondary_thickness_mm,
            notes=notes,
        ))

    return results


def summarize_results(results: List[CalculationResult]) -> Dict[str, object]:
    """Return a summary dict: total checks, passed, failed, failure details."""
    failures = [r for r in results if not r.shielding_adequate]
    return {
        "total_checks": len(results),
        "passed": len(results) - len(failures),
        "failed": len(failures),
        "failures": [
            {
                "component": r.component_id,
                "effect": r.effect_type.value,
                "predicted": r.predicted_dose,
                "limit": r.limit,
                "notes": r.notes,
            }
            for r in failures
        ],
    }
