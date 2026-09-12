"""
Metallic Special Pressurized Equipment (MSPE) analysis logic.

Implements equipment categorization, pressure factor verification, temperature
range checks, hazard level determination, and leak-before-burst applicability
per ECSS-E-ST-32 clause 4.6.1.  stdlib only — no third-party dependencies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class EquipmentType(str, Enum):
    BATTERY = "BATTERY"
    HEAT_PIPE = "HEAT_PIPE"
    LHP = "LHP"                        # loop heat pipe
    CPL = "CPL"                        # capillary pumped loop
    CRYOSTAT = "CRYOSTAT"
    SEALED_CONTAINER = "SEALED_CONTAINER"
    HAZARDOUS_CONTAINER = "HAZARDOUS_CONTAINER"


class HazardLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Pressure verification factors (ECSS-E-ST-32 §4.6.1 basis)
PROOF_FACTOR: float = 1.5    # proof pressure / MAWP
BURST_FACTOR: float = 2.0    # burst pressure / MAWP (metallic, fracture controlled)
PROOF_OVER_TEST_WARN: float = 3.0   # warn when proof >> MAWP (over-test risk)

# Minimum metallic wall thickness (mm)
MIN_WALL_THICKNESS_MM: float = 0.5

# Operating temperature limits (K) per equipment family
_TEMP_LIMITS: dict = {
    EquipmentType.BATTERY:             (233.15, 333.15),   # −40 °C … +60 °C
    EquipmentType.HEAT_PIPE:           (173.15, 473.15),   # −100 °C … +200 °C
    EquipmentType.LHP:                 (173.15, 473.15),
    EquipmentType.CPL:                 (173.15, 473.15),
    EquipmentType.CRYOSTAT:            (4.0,    120.0),    # cryogenic regime
    EquipmentType.SEALED_CONTAINER:    (233.15, 423.15),   # −40 °C … +150 °C
    EquipmentType.HAZARDOUS_CONTAINER: (233.15, 423.15),
}

KNOWN_TYPES: frozenset = frozenset(e.value for e in EquipmentType)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MSPEItem:
    equipment_id: str
    equipment_type: str          # raw string; validated during assessment
    mawp_pa: float               # maximum allowable working pressure (Pa)
    proof_pressure_pa: float     # demonstrated proof pressure (Pa)
    burst_pressure_pa: float     # demonstrated or rated burst pressure (Pa)
    operating_temp_k: float      # nominal operating temperature (K)
    wall_thickness_mm: float     # metallic pressure boundary wall thickness (mm)
    contains_hazardous: bool     # True when working fluid is hazardous
    volume_liters: float         # internal free volume (L)


@dataclass
class MSPEFinding:
    equipment_id: str
    finding_type: str            # "error" | "warning" | "info"
    message: str


@dataclass
class MSPEResult:
    equipment_id: str
    equipment_type: str
    compliant: bool
    hazard_level: str
    findings: List[MSPEFinding] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_type(raw: str) -> Optional[EquipmentType]:
    try:
        return EquipmentType(raw.strip().upper())
    except ValueError:
        return None


def _derive_hazard_level(item: MSPEItem, eq_type: EquipmentType) -> HazardLevel:
    """Derive hazard level from equipment family, pressure, and fluid nature."""
    if item.contains_hazardous:
        if item.mawp_pa > 500_000:   # > 5 bar — high energy + hazardous fluid
            return HazardLevel.CRITICAL
        return HazardLevel.HIGH

    if eq_type == EquipmentType.CRYOSTAT:
        return HazardLevel.HIGH       # cryogenic implosion/pressure-rise risk

    if eq_type == EquipmentType.BATTERY:
        return HazardLevel.MEDIUM     # electrolyte vapour under pressure

    if item.mawp_pa > 300_000:        # > 3 bar non-hazardous
        return HazardLevel.MEDIUM

    return HazardLevel.LOW


# ---------------------------------------------------------------------------
# Core assessment
# ---------------------------------------------------------------------------

def assess_item(item: MSPEItem) -> MSPEResult:
    """Assess one MSPE item; return a result with a list of findings."""
    findings: List[MSPEFinding] = []

    def _err(msg: str) -> None:
        findings.append(MSPEFinding(item.equipment_id, "error", msg))

    def _warn(msg: str) -> None:
        findings.append(MSPEFinding(item.equipment_id, "warning", msg))

    # --- equipment type validation -------------------------------------------
    eq_type = _resolve_type(item.equipment_type)
    if eq_type is None:
        _err(
            f"Unknown equipment type '{item.equipment_type}'. "
            f"Accepted values: {sorted(KNOWN_TYPES)}."
        )
        return MSPEResult(
            item.equipment_id, item.equipment_type, False,
            HazardLevel.HIGH.value, findings
        )

    # --- basic numeric sanity -------------------------------------------------
    if item.mawp_pa <= 0:
        _err(f"MAWP must be positive; got {item.mawp_pa} Pa.")
    if item.proof_pressure_pa <= 0:
        _err(f"Proof pressure must be positive; got {item.proof_pressure_pa} Pa.")
    if item.burst_pressure_pa <= 0:
        _err(f"Burst pressure must be positive; got {item.burst_pressure_pa} Pa.")
    if item.wall_thickness_mm < MIN_WALL_THICKNESS_MM:
        _err(
            f"Wall thickness {item.wall_thickness_mm} mm is below the minimum "
            f"{MIN_WALL_THICKNESS_MM} mm for metallic MSPE."
        )
    if item.volume_liters <= 0:
        _err(f"Internal volume must be positive; got {item.volume_liters} L.")

    # --- temperature range ----------------------------------------------------
    t_min, t_max = _TEMP_LIMITS[eq_type]
    if not (t_min <= item.operating_temp_k <= t_max):
        _err(
            f"Operating temperature {item.operating_temp_k} K is outside "
            f"the allowable range [{t_min}, {t_max}] K for {eq_type.value}."
        )

    # --- proof pressure factor ------------------------------------------------
    if item.mawp_pa > 0:
        required_proof = PROOF_FACTOR * item.mawp_pa
        if item.proof_pressure_pa < required_proof:
            _err(
                f"Proof pressure {item.proof_pressure_pa:.1f} Pa is below the "
                f"required {required_proof:.1f} Pa ({PROOF_FACTOR}× MAWP)."
            )
        if item.proof_pressure_pa > PROOF_OVER_TEST_WARN * item.mawp_pa:
            _warn(
                f"Proof pressure {item.proof_pressure_pa:.1f} Pa exceeds "
                f"{PROOF_OVER_TEST_WARN}× MAWP; verify the vessel is not over-tested."
            )

    # --- burst pressure factor ------------------------------------------------
    if item.mawp_pa > 0:
        required_burst = BURST_FACTOR * item.mawp_pa
        if item.burst_pressure_pa < required_burst:
            _err(
                f"Burst pressure {item.burst_pressure_pa:.1f} Pa is below the "
                f"required {required_burst:.1f} Pa ({BURST_FACTOR}× MAWP)."
            )

    # --- hazardous container volume sanity -----------------------------------
    if eq_type == EquipmentType.HAZARDOUS_CONTAINER and item.volume_liters < 0.01:
        _warn(
            "Hazardous container volume < 0.01 L; verify that the containment "
            "category assignment is correct."
        )

    # --- result assembly ------------------------------------------------------
    hazard = _derive_hazard_level(item, eq_type)
    errors = [f for f in findings if f.finding_type == "error"]
    return MSPEResult(
        equipment_id=item.equipment_id,
        equipment_type=eq_type.value,
        compliant=len(errors) == 0,
        hazard_level=hazard.value,
        findings=findings,
    )


def assess_inventory(items: List[MSPEItem]) -> Tuple[List[MSPEResult], bool]:
    """Assess a collection of MSPE items; return results and overall pass flag."""
    results = [assess_item(i) for i in items]
    overall = all(r.compliant for r in results)
    return results, overall


# ---------------------------------------------------------------------------
# Standalone calculation helpers
# ---------------------------------------------------------------------------

def pressure_margin(mawp_pa: float, applied_pa: float) -> float:
    """
    Return margin-of-safety for a pressure check: (mawp_pa / applied_pa) − 1.
    A positive value means the MAWP is not exceeded; negative means exceedance.
    """
    if applied_pa <= 0:
        raise ValueError(f"applied_pa must be positive; got {applied_pa}.")
    if mawp_pa <= 0:
        raise ValueError(f"mawp_pa must be positive; got {mawp_pa}.")
    return (mawp_pa / applied_pa) - 1.0


def leak_before_burst_applicable(
    wall_thickness_mm: float,
    fracture_toughness_mpa_sqrt_m: float,
    yield_strength_mpa: float,
) -> bool:
    """
    Determine whether the leak-before-burst (LBB) criterion applies.

    LBB is considered applicable when the characteristic crack-tip length
    scale (K_Ic / sigma_y)² is smaller than one-tenth of the wall thickness
    (in mm), meaning a through-wall crack remains stable long enough to leak
    before propagating to catastrophic fracture.

    Parameters
    ----------
    wall_thickness_mm           : metallic wall thickness (mm)
    fracture_toughness_mpa_sqrt_m : plane-strain fracture toughness K_Ic (MPa √m)
    yield_strength_mpa          : 0.2 % proof strength of the wall material (MPa)

    Returns
    -------
    True if LBB is applicable, False otherwise.
    """
    if wall_thickness_mm <= 0:
        raise ValueError(f"wall_thickness_mm must be positive; got {wall_thickness_mm}.")
    if fracture_toughness_mpa_sqrt_m <= 0:
        raise ValueError(
            f"fracture_toughness_mpa_sqrt_m must be positive; got {fracture_toughness_mpa_sqrt_m}."
        )
    if yield_strength_mpa <= 0:
        raise ValueError(f"yield_strength_mpa must be positive; got {yield_strength_mpa}.")

    crack_scale = (fracture_toughness_mpa_sqrt_m / yield_strength_mpa) ** 2
    threshold = wall_thickness_mm / 10.0
    return crack_scale < threshold


def temperature_margin_k(operating_k: float, limit_k: float) -> float:
    """Return temperature margin to a limit: limit_k − operating_k (positive = within limit)."""
    return limit_k - operating_k
