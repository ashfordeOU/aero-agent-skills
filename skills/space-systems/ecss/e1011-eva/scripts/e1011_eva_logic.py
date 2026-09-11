"""
EVA and planetary surface activity engineering logic.
Reference: ECSS-E-ST-10-11C §4.7.10 — paraphrased into implementable procedure.
Stdlib only; offline; deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class SurfaceType(str, Enum):
    MICROGRAVITY = "microgravity"
    LUNAR = "lunar"
    MARTIAN = "martian"
    ISS_EXTERIOR = "iss_exterior"


class OperationClass(str, Enum):
    ONE_HAND = "one_hand"
    TWO_HAND = "two_hand"


# Maximum suited-crewmember force by operation class (Newtons)
_FORCE_LIMIT_N: dict[str, float] = {
    OperationClass.ONE_HAND: 111.0,
    OperationClass.TWO_HAND: 222.0,
}

# Nominal translation speeds by surface type (metres per minute)
_TRANSLATION_SPEED_M_MIN: dict[str, float] = {
    SurfaceType.MICROGRAVITY: 6.0,
    SurfaceType.LUNAR: 2.0,
    SurfaceType.MARTIAN: 1.5,
    SurfaceType.ISS_EXTERIOR: 8.0,
}

# Maximum terrain slope by surface type (degrees); 0 means N/A
_MAX_SLOPE_DEG: dict[str, float] = {
    SurfaceType.MICROGRAVITY: 0.0,
    SurfaceType.LUNAR: 20.0,
    SurfaceType.MARTIAN: 15.0,
    SurfaceType.ISS_EXTERIOR: 0.0,
}

_VALID_SURFACES = {s.value for s in SurfaceType}
_VALID_OP_CLASSES = {oc.value for oc in OperationClass}

# Required life-support margin over planned duration (fraction)
_LIFE_SUPPORT_MARGIN = 0.25


# ---------------------------------------------------------------------------
# Suit interface
# ---------------------------------------------------------------------------

@dataclass
class SuitInterface:
    cabin_pressure_kpa: float
    suit_operating_pressure_kpa: float
    life_support_duration_h: float
    required_duration_h: float
    suit_min_temp_c: float
    suit_max_temp_c: float
    environment_min_temp_c: float
    environment_max_temp_c: float


@dataclass
class SuitCompatibilityResult:
    compatible: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def check_suit_interface(suit: SuitInterface) -> SuitCompatibilityResult:
    """
    Verify suit interface parameters against EVA activity requirements.

    Raises ValueError for non-positive physical quantities.
    Returns SuitCompatibilityResult with issues (blocking) and warnings (advisory).
    """
    if suit.cabin_pressure_kpa <= 0:
        raise ValueError("cabin_pressure_kpa must be positive")
    if suit.suit_operating_pressure_kpa <= 0:
        raise ValueError("suit_operating_pressure_kpa must be positive")
    if suit.life_support_duration_h <= 0:
        raise ValueError("life_support_duration_h must be positive")
    if suit.required_duration_h <= 0:
        raise ValueError("required_duration_h must be positive")
    if suit.suit_min_temp_c >= suit.suit_max_temp_c:
        raise ValueError("suit_min_temp_c must be less than suit_max_temp_c")

    issues: List[str] = []
    warnings: List[str] = []

    required_with_margin = suit.required_duration_h * (1.0 + _LIFE_SUPPORT_MARGIN)
    if suit.life_support_duration_h < required_with_margin:
        issues.append(
            f"Life support endurance {suit.life_support_duration_h:.2f} h insufficient: "
            f"requires {required_with_margin:.2f} h "
            f"({_LIFE_SUPPORT_MARGIN*100:.0f}% margin over {suit.required_duration_h:.2f} h planned)"
        )

    if suit.suit_operating_pressure_kpa >= suit.cabin_pressure_kpa:
        warnings.append(
            f"Suit operating pressure {suit.suit_operating_pressure_kpa:.1f} kPa "
            f">= cabin pressure {suit.cabin_pressure_kpa:.1f} kPa: "
            "pre-breathe protocol required to mitigate decompression sickness risk"
        )

    if suit.environment_min_temp_c < suit.suit_min_temp_c:
        issues.append(
            f"Environment minimum {suit.environment_min_temp_c:.1f} °C is below "
            f"suit thermal floor {suit.suit_min_temp_c:.1f} °C"
        )

    if suit.environment_max_temp_c > suit.suit_max_temp_c:
        issues.append(
            f"Environment maximum {suit.environment_max_temp_c:.1f} °C exceeds "
            f"suit thermal ceiling {suit.suit_max_temp_c:.1f} °C"
        )

    return SuitCompatibilityResult(
        compatible=len(issues) == 0,
        issues=issues,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Tool assessment
# ---------------------------------------------------------------------------

@dataclass
class EvaTool:
    name: str
    max_operator_force_n: float
    required_force_n: float
    reach_m: float
    required_reach_m: float
    operation_class: str      # "one_hand" or "two_hand"
    gloved_grip_compatible: bool


@dataclass
class ToolAssessmentResult:
    suitable: bool
    issues: List[str] = field(default_factory=list)


def assess_tool(tool: EvaTool) -> ToolAssessmentResult:
    """
    Assess whether an EVA tool meets force, reach, and grip requirements.

    Raises ValueError for invalid inputs.
    Returns ToolAssessmentResult; suitable is True only when issues is empty.
    """
    if tool.max_operator_force_n <= 0:
        raise ValueError("max_operator_force_n must be positive")
    if tool.required_force_n < 0:
        raise ValueError("required_force_n must be non-negative")
    if tool.reach_m <= 0:
        raise ValueError("reach_m must be positive")
    if tool.required_reach_m < 0:
        raise ValueError("required_reach_m must be non-negative")
    if tool.operation_class not in _VALID_OP_CLASSES:
        raise ValueError(
            f"operation_class must be one of {sorted(_VALID_OP_CLASSES)}, "
            f"got {tool.operation_class!r}"
        )

    issues: List[str] = []

    if tool.required_force_n > tool.max_operator_force_n:
        issues.append(
            f"Tool '{tool.name}' requires {tool.required_force_n:.1f} N but "
            f"operator maximum is {tool.max_operator_force_n:.1f} N"
        )

    class_limit = _FORCE_LIMIT_N[OperationClass(tool.operation_class)]
    if tool.required_force_n > class_limit:
        issues.append(
            f"Tool '{tool.name}' required force {tool.required_force_n:.1f} N exceeds "
            f"{tool.operation_class} class limit {class_limit:.1f} N"
        )

    if tool.reach_m < tool.required_reach_m:
        issues.append(
            f"Tool '{tool.name}' reach {tool.reach_m:.2f} m is less than "
            f"required {tool.required_reach_m:.2f} m"
        )

    if not tool.gloved_grip_compatible:
        issues.append(
            f"Tool '{tool.name}' handle is not compatible with EVA pressure glove"
        )

    return ToolAssessmentResult(suitable=len(issues) == 0, issues=issues)


# ---------------------------------------------------------------------------
# Mobility assessment
# ---------------------------------------------------------------------------

@dataclass
class MobilityAssessment:
    surface_type: str
    translation_distance_m: float
    allowed_time_min: float
    terrain_slope_deg: float = 0.0


@dataclass
class MobilityResult:
    feasible: bool
    estimated_time_min: float
    issues: List[str] = field(default_factory=list)


def evaluate_mobility(mob: MobilityAssessment) -> MobilityResult:
    """
    Evaluate translation time feasibility and terrain trafficability.

    Raises ValueError for invalid inputs.
    Returns MobilityResult; feasible is True only when issues is empty.
    """
    if mob.surface_type not in _VALID_SURFACES:
        raise ValueError(
            f"surface_type must be one of {sorted(_VALID_SURFACES)}, "
            f"got {mob.surface_type!r}"
        )
    if mob.translation_distance_m < 0:
        raise ValueError("translation_distance_m must be non-negative")
    if mob.allowed_time_min <= 0:
        raise ValueError("allowed_time_min must be positive")
    if mob.terrain_slope_deg < 0:
        raise ValueError("terrain_slope_deg must be non-negative")

    issues: List[str] = []
    surface = SurfaceType(mob.surface_type)

    max_slope = _MAX_SLOPE_DEG[surface]
    if max_slope > 0 and mob.terrain_slope_deg > max_slope:
        issues.append(
            f"Terrain slope {mob.terrain_slope_deg:.1f}° exceeds "
            f"{surface.value} trafficability limit {max_slope:.1f}°"
        )

    speed = _TRANSLATION_SPEED_M_MIN[surface]
    estimated_time_min = mob.translation_distance_m / speed

    if estimated_time_min > mob.allowed_time_min:
        issues.append(
            f"Estimated translation time {estimated_time_min:.1f} min exceeds "
            f"allowed {mob.allowed_time_min:.1f} min "
            f"({mob.translation_distance_m:.0f} m at {speed:.1f} m/min on {surface.value})"
        )

    return MobilityResult(
        feasible=len(issues) == 0,
        estimated_time_min=estimated_time_min,
        issues=issues,
    )


# ---------------------------------------------------------------------------
# Consumable margin
# ---------------------------------------------------------------------------

@dataclass
class ConsumablePlan:
    o2_supply_kg: float
    o2_consumption_rate_kg_h: float
    power_supply_wh: float
    power_consumption_w: float
    coolant_capacity_wh: float
    metabolic_rate_w: float
    duration_h: float
    required_margin_fraction: float = 0.25


@dataclass
class ConsumableResult:
    adequate: bool
    o2_remaining_kg: float
    power_remaining_wh: float
    coolant_remaining_wh: float
    issues: List[str] = field(default_factory=list)


def compute_consumable_margin(plan: ConsumablePlan) -> ConsumableResult:
    """
    Compute end-of-EVA consumable remainders against required reserve fraction.

    Raises ValueError for non-positive or out-of-range inputs.
    Returns ConsumableResult; adequate is True only when issues is empty.
    """
    if plan.o2_supply_kg <= 0:
        raise ValueError("o2_supply_kg must be positive")
    if plan.o2_consumption_rate_kg_h < 0:
        raise ValueError("o2_consumption_rate_kg_h must be non-negative")
    if plan.power_supply_wh <= 0:
        raise ValueError("power_supply_wh must be positive")
    if plan.power_consumption_w < 0:
        raise ValueError("power_consumption_w must be non-negative")
    if plan.coolant_capacity_wh <= 0:
        raise ValueError("coolant_capacity_wh must be positive")
    if plan.metabolic_rate_w < 0:
        raise ValueError("metabolic_rate_w must be non-negative")
    if plan.duration_h <= 0:
        raise ValueError("duration_h must be positive")
    if not (0 < plan.required_margin_fraction < 1):
        raise ValueError("required_margin_fraction must be in (0, 1) exclusive")

    issues: List[str] = []
    pct = plan.required_margin_fraction * 100

    o2_used = plan.o2_consumption_rate_kg_h * plan.duration_h
    o2_remaining = plan.o2_supply_kg - o2_used
    o2_reserve = plan.o2_supply_kg * plan.required_margin_fraction
    if o2_remaining < o2_reserve:
        issues.append(
            f"O2 margin insufficient: {o2_remaining:.3f} kg remaining < "
            f"{o2_reserve:.3f} kg required ({pct:.0f}% of {plan.o2_supply_kg:.3f} kg supply)"
        )

    power_used = plan.power_consumption_w * plan.duration_h
    power_remaining = plan.power_supply_wh - power_used
    power_reserve = plan.power_supply_wh * plan.required_margin_fraction
    if power_remaining < power_reserve:
        issues.append(
            f"Power margin insufficient: {power_remaining:.1f} Wh remaining < "
            f"{power_reserve:.1f} Wh required ({pct:.0f}% of {plan.power_supply_wh:.1f} Wh supply)"
        )

    heat_generated = plan.metabolic_rate_w * plan.duration_h
    coolant_remaining = plan.coolant_capacity_wh - heat_generated
    coolant_reserve = plan.coolant_capacity_wh * plan.required_margin_fraction
    if coolant_remaining < coolant_reserve:
        issues.append(
            f"Coolant margin insufficient: {coolant_remaining:.1f} Wh remaining < "
            f"{coolant_reserve:.1f} Wh required ({pct:.0f}% of {plan.coolant_capacity_wh:.1f} Wh capacity)"
        )

    return ConsumableResult(
        adequate=len(issues) == 0,
        o2_remaining_kg=o2_remaining,
        power_remaining_wh=power_remaining,
        coolant_remaining_wh=coolant_remaining,
        issues=issues,
    )


# ---------------------------------------------------------------------------
# Abort timeline
# ---------------------------------------------------------------------------

@dataclass
class AbortScenario:
    airlock_distance_m: float
    surface_type: str
    abort_time_limit_min: float
    consumable_remaining_h: float


@dataclass
class AbortResult:
    safe: bool
    estimated_return_min: float
    issues: List[str] = field(default_factory=list)


def check_abort_timeline(abort: AbortScenario) -> AbortResult:
    """
    Verify abort return time fits within the safe-return limit and consumables
    cover the return duration.

    Raises ValueError for invalid inputs.
    Returns AbortResult; safe is True only when issues is empty.
    """
    if abort.airlock_distance_m < 0:
        raise ValueError("airlock_distance_m must be non-negative")
    if abort.surface_type not in _VALID_SURFACES:
        raise ValueError(
            f"surface_type must be one of {sorted(_VALID_SURFACES)}, "
            f"got {abort.surface_type!r}"
        )
    if abort.abort_time_limit_min <= 0:
        raise ValueError("abort_time_limit_min must be positive")
    if abort.consumable_remaining_h < 0:
        raise ValueError("consumable_remaining_h must be non-negative")

    issues: List[str] = []
    surface = SurfaceType(abort.surface_type)
    speed = _TRANSLATION_SPEED_M_MIN[surface]
    estimated_return_min = abort.airlock_distance_m / speed

    if estimated_return_min > abort.abort_time_limit_min:
        issues.append(
            f"Abort return {estimated_return_min:.1f} min exceeds safe-return limit "
            f"{abort.abort_time_limit_min:.1f} min "
            f"({abort.airlock_distance_m:.0f} m at {speed:.1f} m/min on {surface.value})"
        )

    estimated_return_h = estimated_return_min / 60.0
    if abort.consumable_remaining_h < estimated_return_h:
        issues.append(
            f"Consumable remaining {abort.consumable_remaining_h:.3f} h insufficient "
            f"for {estimated_return_h:.3f} h abort return"
        )

    return AbortResult(
        safe=len(issues) == 0,
        estimated_return_min=estimated_return_min,
        issues=issues,
    )
