"""
Fail-safe compliance logic — ECSS-E-ST-32C clause 6.3.3.

Implements deterministic, offline checks for residual-strength capability,
inspection-interval adequacy, damage detectability, and widespread fatigue
damage (WFD) risk for fail-safe structural items. No external dependencies.
"""

from __future__ import annotations
import math

# ── Constants ────────────────────────────────────────────────────────────────

MIN_INSPECTION_OPPORTUNITIES = 2

ITEM_CATEGORIES = frozenset(["fail-safe", "safe-life", "damage-tolerant"])

DAMAGE_SCENARIOS = frozenset(
    ["element-loss", "through-crack", "partial-crack", "bay-failure"]
)

INSPECTION_METHODS = frozenset(
    ["visual", "dye-penetrant", "magnetic-particle", "ultrasonic", "eddy-current", "x-ray"]
)

DEFAULT_WFD_THRESHOLD = 0.5


# ── Internal validators ──────────────────────────────────────────────────────

def _require_positive(value: float, name: str) -> None:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric, got {type(value).__name__}")
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def _require_non_negative_int(value: int, name: str) -> None:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


# ── Public API ───────────────────────────────────────────────────────────────

def categorize_item(item_type: str) -> str:
    """
    Return the normalized item category for a structural item.

    Accepted values: 'fail-safe', 'safe-life', 'damage-tolerant'.
    Raises TypeError for non-string input; ValueError for unrecognized category.
    """
    if not isinstance(item_type, str):
        raise TypeError(f"item_type must be a string, got {type(item_type).__name__}")
    normalized = item_type.strip().lower()
    if normalized not in ITEM_CATEGORIES:
        raise ValueError(
            f"Unrecognized item category '{item_type}'. "
            f"Expected one of: {sorted(ITEM_CATEGORIES)}"
        )
    return normalized


def validate_damage_scenario(scenario_type: str) -> str:
    """
    Return the normalized damage scenario type.

    Accepted values: 'element-loss', 'through-crack', 'partial-crack', 'bay-failure'.
    Raises TypeError for non-string input; ValueError for unrecognized type.
    """
    if not isinstance(scenario_type, str):
        raise TypeError(f"scenario_type must be a string, got {type(scenario_type).__name__}")
    normalized = scenario_type.strip().lower()
    if normalized not in DAMAGE_SCENARIOS:
        raise ValueError(
            f"Unrecognized damage scenario '{scenario_type}'. "
            f"Expected one of: {sorted(DAMAGE_SCENARIOS)}"
        )
    return normalized


def check_residual_strength(
    residual_strength_kN: float,
    required_load_kN: float,
) -> dict:
    """
    Check whether the damaged structure's residual strength meets the required
    residual load capability (ECSS-E-ST-32C cl. 6.3.3).

    Args:
        residual_strength_kN: Strength of the structure in the damage state (kN).
        required_load_kN:     Required residual load level, typically the design
                              limit load (kN).

    Returns:
        dict with keys:
            compliant (bool)          — True when residual_strength >= required_load.
            margin (float)            — (residual / required) - 1; negative means fail.
            residual_strength_kN (float)
            required_load_kN (float)
    """
    _require_positive(residual_strength_kN, "residual_strength_kN")
    _require_positive(required_load_kN, "required_load_kN")

    margin = residual_strength_kN / required_load_kN - 1.0
    return {
        "compliant": residual_strength_kN >= required_load_kN,
        "margin": round(margin, 6),
        "residual_strength_kN": residual_strength_kN,
        "required_load_kN": required_load_kN,
    }


def estimate_cycles_to_critical(
    initial_size_mm: float,
    critical_size_mm: float,
    growth_rate_mm_per_cycle: float,
) -> int:
    """
    Estimate cycles for damage to grow from initial size to the critical
    (catastrophic-failure) size, using a constant growth-rate model.

    Returns 0 when initial_size >= critical_size (already at or past critical).
    The result is rounded up (ceiling) so the estimate is conservative.

    Args:
        initial_size_mm:          Damage size immediately after the assumed failure (mm).
        critical_size_mm:         Damage size at which catastrophic failure occurs (mm).
        growth_rate_mm_per_cycle: Damage growth rate (mm per load cycle); must be > 0.
    """
    _require_positive(initial_size_mm, "initial_size_mm")
    _require_positive(critical_size_mm, "critical_size_mm")
    _require_positive(growth_rate_mm_per_cycle, "growth_rate_mm_per_cycle")

    if initial_size_mm >= critical_size_mm:
        return 0
    return math.ceil((critical_size_mm - initial_size_mm) / growth_rate_mm_per_cycle)


def check_inspection_detectability(
    damage_size_mm: float,
    detection_threshold_mm: float,
    inspection_method: str,
) -> dict:
    """
    Check whether the damage is reliably detectable by the inspection method.

    The damage is detectable when damage_size >= detection_threshold.

    Args:
        damage_size_mm:         Current (or initial post-failure) damage size (mm).
        detection_threshold_mm: Smallest damage reliably found by the method (mm).
        inspection_method:      Inspection method identifier (see INSPECTION_METHODS).

    Returns:
        dict with keys:
            detectable (bool)
            damage_size_mm (float)
            detection_threshold_mm (float)
            inspection_method (str)
    """
    _require_positive(damage_size_mm, "damage_size_mm")
    _require_positive(detection_threshold_mm, "detection_threshold_mm")
    normalized = inspection_method.strip().lower()
    if normalized not in INSPECTION_METHODS:
        raise ValueError(
            f"Unrecognized inspection method '{inspection_method}'. "
            f"Expected one of: {sorted(INSPECTION_METHODS)}"
        )
    return {
        "detectable": damage_size_mm >= detection_threshold_mm,
        "damage_size_mm": damage_size_mm,
        "detection_threshold_mm": detection_threshold_mm,
        "inspection_method": normalized,
    }


def check_inspection_interval(
    cycles_to_critical: int,
    inspection_interval_cycles: int,
    min_opportunities: int = MIN_INSPECTION_OPPORTUNITIES,
) -> dict:
    """
    Check whether the inspection interval allows at least `min_opportunities`
    inspections before the damage reaches the critical size.

    Args:
        cycles_to_critical:        Cycles from initial damage to critical size
                                   (use estimate_cycles_to_critical).
        inspection_interval_cycles: Interval between successive inspections (cycles).
        min_opportunities:         Minimum required inspections in the window
                                   (default: MIN_INSPECTION_OPPORTUNITIES = 2).

    Returns:
        dict with keys:
            compliant (bool)
            opportunities (int)           — floor(cycles_to_critical / interval).
            cycles_to_critical (int)
            inspection_interval_cycles (int)
            min_opportunities_required (int)
    """
    _require_non_negative_int(cycles_to_critical, "cycles_to_critical")
    _require_positive(inspection_interval_cycles, "inspection_interval_cycles")
    _require_positive(min_opportunities, "min_opportunities")

    opportunities = 0 if cycles_to_critical == 0 else cycles_to_critical // inspection_interval_cycles
    return {
        "compliant": opportunities >= min_opportunities,
        "opportunities": opportunities,
        "cycles_to_critical": cycles_to_critical,
        "inspection_interval_cycles": inspection_interval_cycles,
        "min_opportunities_required": min_opportunities,
    }


def check_wfd_potential(
    element_count: int,
    individual_life_cycles: int,
    inspection_interval_cycles: int,
    wfd_threshold_fraction: float = DEFAULT_WFD_THRESHOLD,
) -> dict:
    """
    Assess the risk of widespread fatigue damage (WFD) across a group of similar
    structural elements.

    WFD risk is flagged when the fraction of individual fatigue life consumed
    within one inspection interval equals or exceeds wfd_threshold_fraction,
    indicating that a significant portion of the element population could fail
    between consecutive inspections.

    Args:
        element_count:              Number of similar structural elements.
        individual_life_cycles:     Fatigue life of each individual element (cycles).
        inspection_interval_cycles: Interval between inspections (cycles).
        wfd_threshold_fraction:     Consumed-fraction threshold for WFD flag
                                    (default 0.5); must be in (0, 1].

    Returns:
        dict with keys:
            wfd_risk (bool)
            consumed_fraction (float)     — inspection_interval / individual_life.
            element_count (int)
            individual_life_cycles (int)
            inspection_interval_cycles (int)
            wfd_threshold_fraction (float)
    """
    _require_positive(element_count, "element_count")
    _require_positive(individual_life_cycles, "individual_life_cycles")
    _require_positive(inspection_interval_cycles, "inspection_interval_cycles")
    if not (0.0 < wfd_threshold_fraction <= 1.0):
        raise ValueError(
            f"wfd_threshold_fraction must be in (0, 1], got {wfd_threshold_fraction}"
        )

    consumed_fraction = inspection_interval_cycles / individual_life_cycles
    return {
        "wfd_risk": consumed_fraction >= wfd_threshold_fraction,
        "consumed_fraction": round(consumed_fraction, 6),
        "element_count": element_count,
        "individual_life_cycles": individual_life_cycles,
        "inspection_interval_cycles": inspection_interval_cycles,
        "wfd_threshold_fraction": wfd_threshold_fraction,
    }


def check_fail_safe_compliance(scenario: dict) -> dict:
    """
    Aggregate fail-safe compliance check for one structural item.

    Runs four sub-checks in sequence: residual strength, inspection interval,
    detectability, and WFD potential. An item is compliant only when all four
    pass.

    Required keys in `scenario`:
        item_id (str)
        damage_scenario (str)              — see DAMAGE_SCENARIOS
        residual_strength_kN (float)
        required_load_kN (float)
        initial_damage_mm (float)
        critical_damage_mm (float)
        growth_rate_mm_per_cycle (float)
        inspection_interval_cycles (int)
        inspection_method (str)            — see INSPECTION_METHODS
        detection_threshold_mm (float)
        element_count (int)
        element_fatigue_life_cycles (int)

    Returns:
        dict with keys:
            item_id (str)
            compliant (bool)
            findings (list[str])             — empty when compliant.
            residual_strength_check (dict)
            inspection_interval_check (dict)
            detectability_check (dict)
            wfd_check (dict)
    """
    required_keys = [
        "item_id", "damage_scenario",
        "residual_strength_kN", "required_load_kN",
        "initial_damage_mm", "critical_damage_mm", "growth_rate_mm_per_cycle",
        "inspection_interval_cycles", "inspection_method", "detection_threshold_mm",
        "element_count", "element_fatigue_life_cycles",
    ]
    missing = [k for k in required_keys if k not in scenario]
    if missing:
        raise ValueError(f"Missing required keys in scenario: {missing}")

    validate_damage_scenario(scenario["damage_scenario"])

    findings: list[str] = []

    rs = check_residual_strength(
        float(scenario["residual_strength_kN"]),
        float(scenario["required_load_kN"]),
    )
    if not rs["compliant"]:
        findings.append(
            f"Residual strength {scenario['residual_strength_kN']} kN < "
            f"required {scenario['required_load_kN']} kN (margin {rs['margin']:.4f})"
        )

    cycles = estimate_cycles_to_critical(
        float(scenario["initial_damage_mm"]),
        float(scenario["critical_damage_mm"]),
        float(scenario["growth_rate_mm_per_cycle"]),
    )
    insp = check_inspection_interval(cycles, int(scenario["inspection_interval_cycles"]))
    if not insp["compliant"]:
        findings.append(
            f"Inspection interval {scenario['inspection_interval_cycles']} cycles provides "
            f"only {insp['opportunities']} opportunit(ies) before critical damage "
            f"({cycles} cycles); {MIN_INSPECTION_OPPORTUNITIES} required"
        )

    det = check_inspection_detectability(
        float(scenario["initial_damage_mm"]),
        float(scenario["detection_threshold_mm"]),
        str(scenario["inspection_method"]),
    )
    if not det["detectable"]:
        findings.append(
            f"Initial damage {scenario['initial_damage_mm']} mm < detection threshold "
            f"{scenario['detection_threshold_mm']} mm for method '{det['inspection_method']}'"
        )

    wfd = check_wfd_potential(
        int(scenario["element_count"]),
        int(scenario["element_fatigue_life_cycles"]),
        int(scenario["inspection_interval_cycles"]),
    )
    if wfd["wfd_risk"]:
        findings.append(
            f"WFD risk: {wfd['consumed_fraction']:.4f} of element fatigue life consumed "
            f"per inspection interval (threshold {wfd['wfd_threshold_fraction']})"
        )

    return {
        "item_id": scenario["item_id"],
        "compliant": len(findings) == 0,
        "findings": findings,
        "residual_strength_check": rs,
        "inspection_interval_check": insp,
        "detectability_check": det,
        "wfd_check": wfd,
    }
